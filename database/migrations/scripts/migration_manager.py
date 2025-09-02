#!/usr/bin/env python3
"""
ComplianceAI Database Migration Manager
=====================================

This script manages database migrations for both PostgreSQL and MongoDB.
It provides functionality to:
- Apply migrations in order
- Rollback migrations
- Check migration status
- Validate migration integrity
- Generate migration reports

Usage:
    python migration_manager.py [command] [options]

Commands:
    apply        Apply pending migrations
    rollback     Rollback applied migrations
    status       Show migration status
    validate     Validate migration integrity
    report       Generate migration report

Options:
    --db-type    Database type (postgresql|mongodb|all) [default: all]
    --target     Target migration version [default: latest]
    --force      Force operation without confirmation
    --dry-run    Show what would be done without executing
    --verbose    Enable verbose output

Environment Variables:
    DB_HOST          Database host
    DB_PORT          Database port
    DB_NAME          Database name
    DB_USER          Database user
    DB_PASSWORD      Database password
    MONGODB_URL      MongoDB connection URL
    MIGRATION_PATH   Path to migration files

Author: ComplianceAI Development Team
"""

import os
import sys
import argparse
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Database connectors
import psycopg2
from psycopg2.extras import RealDictCursor
import pymongo
from pymongo import MongoClient


class MigrationManager:
    """Database migration manager for ComplianceAI"""

    def __init__(self, db_type: str = 'all', verbose: bool = False):
        self.db_type = db_type
        self.verbose = verbose
        self.logger = self._setup_logger()

        # Database connections
        self.pg_conn = None
        self.mongo_client = None

        # Migration paths
        self.migration_base_path = Path(__file__).parent.parent
        self.pg_migration_path = self.migration_base_path / 'postgresql'
        self.mongo_migration_path = self.migration_base_path / 'mongodb'

        # Load configuration
        self.config = self._load_config()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('MigrationManager')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {
            'postgresql': {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '5432')),
                'database': os.getenv('DB_NAME', 'complianceai'),
                'user': os.getenv('DB_USER', 'complianceai'),
                'password': os.getenv('DB_PASSWORD', ''),
                'ssl_mode': os.getenv('DB_SSL_MODE', 'require')
            },
            'mongodb': {
                'url': os.getenv('MONGODB_URL', 'mongodb://localhost:27017/complianceai'),
                'database': os.getenv('MONGODB_DB', 'complianceai')
            },
            'migration_path': os.getenv('MIGRATION_PATH', str(self.migration_base_path))
        }
        return config

    def connect_databases(self):
        """Connect to databases"""
        try:
            if self.db_type in ['postgresql', 'all']:
                self.logger.info("Connecting to PostgreSQL...")
                self.pg_conn = psycopg2.connect(
                    host=self.config['postgresql']['host'],
                    port=self.config['postgresql']['port'],
                    database=self.config['postgresql']['database'],
                    user=self.config['postgresql']['user'],
                    password=self.config['postgresql']['password'],
                    sslmode=self.config['postgresql']['ssl_mode']
                )
                self.pg_conn.autocommit = False
                self.logger.info("PostgreSQL connection established")

            if self.db_type in ['mongodb', 'all']:
                self.logger.info("Connecting to MongoDB...")
                self.mongo_client = MongoClient(self.config['mongodb']['url'])
                self.mongo_db = self.mongo_client[self.config['mongodb']['database']]
                self.logger.info("MongoDB connection established")

        except Exception as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            sys.exit(1)

    def disconnect_databases(self):
        """Disconnect from databases"""
        if self.pg_conn:
            self.pg_conn.close()
            self.logger.info("PostgreSQL connection closed")

        if self.mongo_client:
            self.mongo_client.close()
            self.logger.info("MongoDB connection closed")

    def get_migration_files(self, db_type: str) -> List[Path]:
        """Get migration files for database type"""
        if db_type == 'postgresql':
            migration_path = self.pg_migration_path
        elif db_type == 'mongodb':
            migration_path = self.mongo_migration_path
        else:
            raise ValueError(f"Invalid database type: {db_type}")

        if not migration_path.exists():
            return []

        migration_files = []
        for file_path in migration_path.glob('*.sql' if db_type == 'postgresql' else '*.js'):
            migration_files.append(file_path)

        # Sort by version number
        migration_files.sort(key=lambda x: self._extract_version(x.name))

        return migration_files

    def _extract_version(self, filename: str) -> int:
        """Extract version number from migration filename"""
        # Expected format: XXX_description.ext
        version_part = filename.split('_')[0]
        try:
            return int(version_part)
        except ValueError:
            return 999  # Put invalid versions at the end

    def get_applied_migrations(self, db_type: str) -> List[Dict[str, Any]]:
        """Get list of applied migrations"""
        try:
            if db_type == 'postgresql':
                with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT version, description, applied_at, applied_by,
                               success, checksum
                        FROM regulatory.migrations
                        ORDER BY version
                    """)
                    return [dict(row) for row in cursor.fetchall()]

            elif db_type == 'mongodb':
                migrations = list(self.mongo_db.migrations.find(
                    {}, {'_id': 0}
                ).sort('version', 1))
                return migrations

        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {str(e)}")
            return []

    def calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def apply_migration(self, db_type: str, migration_file: Path, dry_run: bool = False) -> bool:
        """Apply a single migration"""
        version = self._extract_version(migration_file.name)
        self.logger.info(f"Applying {db_type} migration {version}: {migration_file.name}")

        try:
            # Read migration content
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()

            checksum = self.calculate_checksum(content)

            if dry_run:
                self.logger.info(f"[DRY RUN] Would apply migration {version} with checksum {checksum}")
                return True

            if db_type == 'postgresql':
                # Apply PostgreSQL migration
                with self.pg_conn.cursor() as cursor:
                    cursor.execute(content)

                    # Record migration
                    cursor.execute("""
                        INSERT INTO regulatory.migrations
                        (version, description, applied_by, checksum, success)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        str(version).zfill(3),
                        f"Applied from {migration_file.name}",
                        os.getenv('USER', 'migration_manager'),
                        checksum,
                        True
                    ))

                self.pg_conn.commit()

            elif db_type == 'mongodb':
                # Apply MongoDB migration
                exec(content)  # Execute JavaScript migration

                # Record migration (should be done in migration file)
                pass

            self.logger.info(f"Successfully applied {db_type} migration {version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply {db_type} migration {version}: {str(e)}")
            if db_type == 'postgresql' and self.pg_conn:
                self.pg_conn.rollback()
            return False

    def rollback_migration(self, db_type: str, version: str, dry_run: bool = False) -> bool:
        """Rollback a migration"""
        self.logger.info(f"Rolling back {db_type} migration {version}")

        try:
            if dry_run:
                self.logger.info(f"[DRY RUN] Would rollback migration {version}")
                return True

            if db_type == 'postgresql':
                # For PostgreSQL, we need rollback scripts (not implemented in this version)
                self.logger.warning("PostgreSQL rollback not implemented - manual intervention required")
                return False

            elif db_type == 'mongodb':
                # For MongoDB, we can drop collections or run rollback scripts
                self.logger.warning("MongoDB rollback not implemented - manual intervention required")
                return False

        except Exception as e:
            self.logger.error(f"Failed to rollback {db_type} migration {version}: {str(e)}")
            return False

    def check_migration_status(self, db_type: str) -> Dict[str, Any]:
        """Check migration status for database type"""
        migration_files = self.get_migration_files(db_type)
        applied_migrations = self.get_applied_migrations(db_type)

        applied_versions = {m['version'] for m in applied_migrations}

        status = {
            'total_files': len(migration_files),
            'applied_count': len(applied_migrations),
            'pending_count': 0,
            'failed_count': 0,
            'pending_migrations': [],
            'failed_migrations': [],
            'latest_applied': None
        }

        for migration_file in migration_files:
            version = str(self._extract_version(migration_file.name)).zfill(3)
            if version not in applied_versions:
                status['pending_migrations'].append({
                    'version': version,
                    'file': migration_file.name
                })
                status['pending_count'] += 1

        for migration in applied_migrations:
            if not migration.get('success', False):
                status['failed_migrations'].append(migration)
                status['failed_count'] += 1

        if applied_migrations:
            status['latest_applied'] = max(applied_migrations, key=lambda x: x['version'])

        return status

    def validate_migrations(self, db_type: str) -> Dict[str, Any]:
        """Validate migration integrity"""
        validation_results = {
            'valid': True,
            'issues': [],
            'checked_files': 0,
            'checksum_mismatches': 0
        }

        migration_files = self.get_migration_files(db_type)
        applied_migrations = {m['version']: m for m in self.get_applied_migrations(db_type)}

        for migration_file in migration_files:
            version = str(self._extract_version(migration_file.name)).zfill(3)
            validation_results['checked_files'] += 1

            if version in applied_migrations:
                # Check checksum
                with open(migration_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                calculated_checksum = self.calculate_checksum(content)
                stored_checksum = applied_migrations[version].get('checksum')

                if calculated_checksum != stored_checksum:
                    validation_results['valid'] = False
                    validation_results['checksum_mismatches'] += 1
                    validation_results['issues'].append({
                        'type': 'checksum_mismatch',
                        'version': version,
                        'file': migration_file.name,
                        'stored': stored_checksum,
                        'calculated': calculated_checksum
                    })

        return validation_results

    def generate_report(self, db_type: str) -> Dict[str, Any]:
        """Generate migration report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'database_type': db_type,
            'status': self.check_migration_status(db_type),
            'validation': self.validate_migrations(db_type),
            'applied_migrations': self.get_applied_migrations(db_type)
        }

        return report

    def apply_pending_migrations(self, db_type: str, target_version: Optional[str] = None,
                               dry_run: bool = False, force: bool = False) -> bool:
        """Apply all pending migrations"""
        migration_files = self.get_migration_files(db_type)
        applied_migrations = self.get_applied_migrations(db_type)
        applied_versions = {m['version'] for m in applied_migrations}

        success = True

        for migration_file in migration_files:
            version = str(self._extract_version(migration_file.name)).zfill(3)

            if version in applied_versions:
                continue

            if target_version and version > target_version:
                break

            if not dry_run and not force:
                response = input(f"Apply migration {version} ({migration_file.name})? [y/N]: ")
                if response.lower() != 'y':
                    continue

            if not self.apply_migration(db_type, migration_file, dry_run):
                success = False
                if not force:
                    break

        return success

    def print_status(self, db_type: str):
        """Print migration status"""
        status = self.check_migration_status(db_type)

        print(f"\n=== {db_type.upper()} Migration Status ===")
        print(f"Total migration files: {status['total_files']}")
        print(f"Applied migrations: {status['applied_count']}")
        print(f"Pending migrations: {status['pending_count']}")
        print(f"Failed migrations: {status['failed_count']}")

        if status['latest_applied']:
            print(f"Latest applied: {status['latest_applied']['version']} - {status['latest_applied']['description']}")

        if status['pending_migrations']:
            print(f"\nPending migrations:")
            for migration in status['pending_migrations']:
                print(f"  {migration['version']}: {migration['file']}")

        if status['failed_migrations']:
            print(f"\nFailed migrations:")
            for migration in status['failed_migrations']:
                print(f"  {migration['version']}: {migration['description']}")

    def print_validation_report(self, db_type: str):
        """Print validation report"""
        validation = self.validate_migrations(db_type)

        print(f"\n=== {db_type.upper()} Migration Validation ===")
        print(f"Overall status: {'VALID' if validation['valid'] else 'INVALID'}")
        print(f"Files checked: {validation['checked_files']}")
        print(f"Checksum mismatches: {validation['checksum_mismatches']}")

        if validation['issues']:
            print(f"\nIssues found:")
            for issue in validation['issues']:
                print(f"  {issue['type']}: {issue['version']} ({issue['file']})")


def main():
    parser = argparse.ArgumentParser(description='ComplianceAI Database Migration Manager')
    parser.add_argument('command', choices=['apply', 'rollback', 'status', 'validate', 'report'],
                       help='Migration command to execute')
    parser.add_argument('--db-type', choices=['postgresql', 'mongodb', 'all'],
                       default='all', help='Database type to operate on')
    parser.add_argument('--target', help='Target migration version')
    parser.add_argument('--force', action='store_true', help='Force operation without confirmation')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Initialize migration manager
    manager = MigrationManager(args.db_type, args.verbose)

    try:
        # Connect to databases
        manager.connect_databases()

        if args.command == 'apply':
            db_types = [args.db_type] if args.db_type != 'all' else ['postgresql', 'mongodb']

            for db_type in db_types:
                print(f"\nProcessing {db_type} migrations...")
                success = manager.apply_pending_migrations(
                    db_type, args.target, args.dry_run, args.force
                )
                if not success:
                    print(f"Failed to apply {db_type} migrations")
                    sys.exit(1)

            print("Migration application completed")

        elif args.command == 'rollback':
            print("Rollback functionality not yet implemented")
            sys.exit(1)

        elif args.command == 'status':
            db_types = [args.db_type] if args.db_type != 'all' else ['postgresql', 'mongodb']

            for db_type in db_types:
                manager.print_status(db_type)

        elif args.command == 'validate':
            db_types = [args.db_type] if args.db_type != 'all' else ['postgresql', 'mongodb']

            for db_type in db_types:
                manager.print_validation_report(db_type)

        elif args.command == 'report':
            db_types = [args.db_type] if args.db_type != 'all' else ['postgresql', 'mongodb']

            for db_type in db_types:
                report = manager.generate_report(db_type)
                print(json.dumps(report, indent=2, default=str))

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        manager.disconnect_databases()


if __name__ == '__main__':
    main()
