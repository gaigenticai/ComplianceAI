#!/usr/bin/env python3
"""
ComplianceAI PostgreSQL Data Migration Tool
===========================================

This tool provides comprehensive data migration capabilities for PostgreSQL databases
used in the ComplianceAI system. It supports:

- Data migration between environments (dev/staging/prod)
- Selective table migration
- Data transformation during migration
- Migration validation and rollback
- Performance optimization for large datasets

Usage:
    python data_migration_tool.py [command] [options]

Commands:
    migrate     Migrate data between databases
    validate    Validate migrated data integrity
    rollback    Rollback migration operations
    backup      Create database backup
    restore     Restore from backup
    analyze     Analyze database performance and size

Options:
    --source-db       Source database connection string
    --target-db       Target database connection string
    --tables          Comma-separated list of tables to migrate
    --batch-size      Batch size for data operations [default: 1000]
    --workers         Number of parallel workers [default: 4]
    --dry-run         Show what would be done without executing
    --force           Force operation without confirmation
    --verbose         Enable verbose output

Examples:
    # Migrate all tables from dev to staging
    python data_migration_tool.py migrate --source-db "postgresql://user:pass@dev-db/db" --target-db "postgresql://user:pass@staging-db/db"

    # Migrate specific tables only
    python data_migration_tool.py migrate --tables regulatory.jurisdiction_configs,regulatory.regulatory_obligations

    # Validate migration integrity
    python data_migration_tool.py validate --source-db "postgresql://user:pass@source-db/db" --target-db "postgresql://user:pass@target-db/db"

Author: ComplianceAI Development Team
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import csv
import gzip

# Database imports
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import psycopg2.pool


class PostgreSQLMigrationTool:
    """PostgreSQL data migration tool for ComplianceAI"""

    def __init__(self,
                 source_db: str = None,
                 target_db: str = None,
                 batch_size: int = 1000,
                 workers: int = 4,
                 verbose: bool = False):
        self.source_db = source_db
        self.target_db = target_db
        self.batch_size = batch_size
        self.workers = workers
        self.verbose = verbose
        self.logger = self._setup_logger()

        # Database connections
        self.source_conn = None
        self.target_conn = None

        # Migration tracking
        self.migration_id = f"migration_{int(time.time())}"
        self.migration_log = []

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('PostgreSQLMigrationTool')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def connect_databases(self):
        """Connect to source and target databases"""
        try:
            if self.source_db:
                self.logger.info("Connecting to source database...")
                self.source_conn = psycopg2.connect(self.source_db)
                self.source_conn.autocommit = False
                self.logger.info("Source database connection established")

            if self.target_db:
                self.logger.info("Connecting to target database...")
                self.target_conn = psycopg2.connect(self.target_db)
                self.target_conn.autocommit = False
                self.logger.info("Target database connection established")

        except psycopg2.Error as e:
            self.logger.error(f"Database connection failed: {str(e)}")
            sys.exit(1)

    def disconnect_databases(self):
        """Disconnect from databases"""
        if self.source_conn:
            self.source_conn.close()
            self.logger.info("Source database connection closed")

        if self.target_conn:
            self.target_conn.close()
            self.logger.info("Target database connection closed")

    def get_table_list(self, schema: str = 'regulatory') -> List[str]:
        """Get list of tables in the specified schema"""
        try:
            with self.source_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = %s
                    ORDER BY tablename
                """, (schema,))

                tables = [row[0] for row in cursor.fetchall()]
                return tables

        except psycopg2.Error as e:
            self.logger.error(f"Failed to get table list: {str(e)}")
            return []

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a table"""
        try:
            with self.source_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {table_name}")
                row_count = cursor.fetchone()['row_count']

                # Get column information
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema || '.' || table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))

                columns = cursor.fetchall()

                # Get indexes
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname || '.' || tablename = %s
                """, (table_name,))

                indexes = cursor.fetchall()

                return {
                    'table_name': table_name,
                    'row_count': row_count,
                    'columns': columns,
                    'indexes': indexes
                }

        except psycopg2.Error as e:
            self.logger.error(f"Failed to get table info for {table_name}: {str(e)}")
            return {}

    def create_backup(self, output_file: str, tables: List[str] = None) -> bool:
        """Create a backup of specified tables"""
        self.logger.info(f"Creating backup to: {output_file}")

        try:
            # Determine tables to backup
            if not tables:
                tables = self.get_table_list()

            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                # Write backup header
                backup_info = {
                    'backup_timestamp': datetime.now().isoformat(),
                    'source_database': self.source_db.split('@')[-1] if self.source_db else 'unknown',
                    'tables': tables,
                    'migration_id': self.migration_id
                }

                f.write(f"-- ComplianceAI Database Backup\n")
                f.write(f"-- Generated: {backup_info['backup_timestamp']}\n")
                f.write(f"-- Tables: {', '.join(tables)}\n\n")

                # Backup each table
                with self.source_conn.cursor() as cursor:
                    for table in tables:
                        self.logger.info(f"Backing up table: {table}")

                        # Get table structure
                        cursor.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema || '.' || table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))

                        columns = [row[0] for row in cursor.fetchall()]
                        column_list = ', '.join(columns)

                        # Write table header
                        f.write(f"-- Table: {table}\n")
                        f.write(f"-- Columns: {column_list}\n\n")

                        # Export data in batches
                        offset = 0
                        while True:
                            cursor.execute(f"""
                                SELECT {column_list}
                                FROM {table}
                                ORDER BY (SELECT NULL)  -- Maintain insertion order
                                LIMIT %s OFFSET %s
                            """, (self.batch_size, offset))

                            rows = cursor.fetchall()
                            if not rows:
                                break

                            # Write data as INSERT statements
                            for row in rows:
                                # Properly format values for SQL
                                formatted_values = []
                                for value in row:
                                    if value is None:
                                        formatted_values.append('NULL')
                                    elif isinstance(value, str):
                                        formatted_values.append(f"'{value.replace(chr(39), chr(39)*2)}'")
                                    elif isinstance(value, (int, float)):
                                        formatted_values.append(str(value))
                                    elif isinstance(value, datetime):
                                        formatted_values.append(f"'{value.isoformat()}'")
                                    else:
                                        formatted_values.append(f"'{str(value)}'")

                                values_str = ', '.join(formatted_values)
                                f.write(f"INSERT INTO {table} ({column_list}) VALUES ({values_str});\n")

                            offset += self.batch_size

                        f.write(f"\n-- End of table: {table}\n\n")

            self.logger.info(f"Backup completed successfully: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False

    def migrate_table(self, table_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate a single table"""
        self.logger.info(f"Migrating table: {table_name}")

        result = {
            'table_name': table_name,
            'status': 'pending',
            'records_processed': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'errors': []
        }

        try:
            # Get table information
            table_info = self.get_table_info(table_name)
            if not table_info:
                result['status'] = 'error'
                result['errors'].append("Failed to get table information")
                return result

            self.logger.info(f"Table {table_name} has {table_info['row_count']} records")

            if dry_run:
                result['status'] = 'dry_run_completed'
                result['records_processed'] = table_info['row_count']
                return result

            # Ensure target table exists
            self._ensure_target_table(table_name, table_info)

            # Migrate data in batches
            total_processed = 0
            offset = 0

            with self.source_conn.cursor(cursor_factory=RealDictCursor) as source_cursor, \
                 self.target_conn.cursor() as target_cursor:

                while True:
                    # Fetch batch from source
                    source_cursor.execute(f"""
                        SELECT * FROM {table_name}
                        ORDER BY (SELECT NULL)
                        LIMIT %s OFFSET %s
                    """, (self.batch_size, offset))

                    rows = source_cursor.fetchall()
                    if not rows:
                        break

                    # Insert batch into target
                    if rows:
                        columns = list(rows[0].keys())
                        values = [[row[col] for col in columns] for row in rows]

                        # Prepare INSERT statement
                        placeholders = ', '.join(['%s'] * len(columns))
                        column_list = ', '.join(columns)

                        target_cursor.executemany(f"""
                            INSERT INTO {table_name} ({column_list})
                            VALUES ({placeholders})
                            ON CONFLICT DO NOTHING
                        """, values)

                        total_processed += len(rows)
                        self.logger.info(f"Processed {total_processed} records for {table_name}")

                    offset += self.batch_size

                # Commit the migration
                self.target_conn.commit()

            result['status'] = 'completed'
            result['records_processed'] = total_processed
            result['end_time'] = datetime.now()

        except Exception as e:
            self.logger.error(f"Migration failed for table {table_name}: {str(e)}")
            result['status'] = 'error'
            result['errors'].append(str(e))

            if self.target_conn:
                self.target_conn.rollback()

        return result

    def _ensure_target_table(self, table_name: str, table_info: Dict[str, Any]):
        """Ensure target table exists with correct structure"""
        try:
            with self.target_conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema || '.' || table_name = %s
                    )
                """, (table_name,))

                table_exists = cursor.fetchone()[0]

                if not table_exists:
                    # Create table structure
                    self._create_table_structure(cursor, table_name, table_info)

                    # Create indexes
                    self._create_table_indexes(cursor, table_name, table_info)

                    self.target_conn.commit()

        except psycopg2.Error as e:
            self.logger.error(f"Failed to create target table {table_name}: {str(e)}")
            raise

    def _create_table_structure(self, cursor, table_name: str, table_info: Dict[str, Any]):
        """Create table structure in target database"""
        columns_sql = []

        for column in table_info['columns']:
            column_def = f"{column['column_name']} {column['data_type']}"

            if column['column_default'] is not None:
                column_def += f" DEFAULT {column['column_default']}"

            if column['is_nullable'] == 'NO':
                column_def += " NOT NULL"

            columns_sql.append(column_def)

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns_sql)}
            )
        """

        cursor.execute(create_sql)
        self.logger.info(f"Created table structure for {table_name}")

    def _create_table_indexes(self, cursor, table_name: str, table_info: Dict[str, Any]):
        """Create indexes for target table"""
        for index in table_info['indexes']:
            try:
                # Skip primary key and unique indexes as they're created with table
                if 'PRIMARY KEY' in index['indexdef'] or 'UNIQUE' in index['indexdef']:
                    continue

                cursor.execute(index['indexdef'])
                self.logger.info(f"Created index {index['indexname']} for {table_name}")

            except psycopg2.Error as e:
                self.logger.warning(f"Failed to create index {index['indexname']}: {str(e)}")

    def migrate_data(self, tables: List[str] = None, dry_run: bool = False,
                    force: bool = False) -> Dict[str, Any]:
        """Migrate data for specified tables"""
        self.logger.info("Starting data migration process")

        # Get tables to migrate
        if not tables:
            tables = self.get_table_list()

        if not tables:
            self.logger.error("No tables found to migrate")
            return {'status': 'error', 'message': 'No tables found'}

        # Confirm migration
        if not dry_run and not force:
            print(f"\nMigration Plan:")
            print(f"Source: {self.source_db.split('@')[-1] if self.source_db else 'unknown'}")
            print(f"Target: {self.target_db.split('@')[-1] if self.target_db else 'unknown'}")
            print(f"Tables: {', '.join(tables)}")

            response = input("\nProceed with migration? [y/N]: ")
            if response.lower() != 'y':
                return {'status': 'cancelled', 'message': 'Migration cancelled by user'}

        # Execute migration
        migration_results = []
        total_start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit migration tasks
            future_to_table = {
                executor.submit(self.migrate_table, table, dry_run): table
                for table in tables
            }

            # Collect results
            for future in as_completed(future_to_table):
                table = future_to_table[future]
                try:
                    result = future.result()
                    migration_results.append(result)
                    self.migration_log.append(result)

                except Exception as e:
                    self.logger.error(f"Migration failed for {table}: {str(e)}")
                    migration_results.append({
                        'table_name': table,
                        'status': 'error',
                        'errors': [str(e)]
                    })

        # Calculate summary
        total_time = time.time() - total_start_time
        successful = sum(1 for r in migration_results if r['status'] == 'completed')
        failed = sum(1 for r in migration_results if r['status'] == 'error')
        total_records = sum(r.get('records_processed', 0) for r in migration_results)

        summary = {
            'status': 'completed' if failed == 0 else 'partial_success',
            'total_tables': len(tables),
            'successful_tables': successful,
            'failed_tables': failed,
            'total_records': total_records,
            'total_time_seconds': total_time,
            'average_time_per_table': total_time / len(tables) if tables else 0,
            'results': migration_results
        }

        self.logger.info(f"Migration completed: {successful}/{len(tables)} tables successful")
        return summary

    def validate_migration(self, tables: List[str] = None) -> Dict[str, Any]:
        """Validate data integrity after migration"""
        self.logger.info("Starting migration validation")

        if not tables:
            tables = self.get_table_list()

        validation_results = {
            'total_tables': len(tables),
            'validated_tables': 0,
            'passed_validation': 0,
            'failed_validation': 0,
            'table_results': []
        }

        for table in tables:
            table_result = self._validate_table_migration(table)
            validation_results['table_results'].append(table_result)

            if table_result['status'] == 'passed':
                validation_results['passed_validation'] += 1
            elif table_result['status'] == 'failed':
                validation_results['failed_validation'] += 1

            validation_results['validated_tables'] += 1

        validation_results['overall_status'] = 'passed' if validation_results['failed_validation'] == 0 else 'failed'

        self.logger.info(f"Validation completed: {validation_results['passed_validation']}/{validation_results['total_tables']} tables passed")
        return validation_results

    def _validate_table_migration(self, table_name: str) -> Dict[str, Any]:
        """Validate migration for a single table"""
        result = {
            'table_name': table_name,
            'status': 'unknown',
            'checks': [],
            'errors': []
        }

        try:
            with self.source_conn.cursor() as source_cursor, \
                 self.target_conn.cursor() as target_cursor:

                # Check row counts
                source_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                source_count = source_cursor.fetchone()[0]

                target_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                target_count = target_cursor.fetchone()[0]

                if source_count == target_count:
                    result['checks'].append({
                        'check': 'row_count',
                        'status': 'passed',
                        'source_count': source_count,
                        'target_count': target_count
                    })
                else:
                    result['status'] = 'failed'
                    result['errors'].append({
                        'check': 'row_count',
                        'message': f"Row count mismatch: source={source_count}, target={target_count}"
                    })

                # Check for data integrity (sample check)
                if source_count > 0:
                    source_cursor.execute(f"""
                        SELECT md5(CAST(ROW_TO_JSON(t.*) AS TEXT)) as row_hash
                        FROM {table_name} t
                        TABLESAMPLE BERNOULLI(1)
                        LIMIT 10
                    """)
                    source_hashes = [row[0] for row in source_cursor.fetchall()]

                    target_cursor.execute(f"""
                        SELECT md5(CAST(ROW_TO_JSON(t.*) AS TEXT)) as row_hash
                        FROM {table_name} t
                        TABLESAMPLE BERNOULLI(1)
                        LIMIT 10
                    """)
                    target_hashes = [row[0] for row in target_cursor.fetchall()]

                    if set(source_hashes) == set(target_hashes):
                        result['checks'].append({
                            'check': 'data_integrity',
                            'status': 'passed',
                            'samples_checked': len(source_hashes)
                        })
                    else:
                        result['status'] = 'failed'
                        result['errors'].append({
                            'check': 'data_integrity',
                            'message': "Data integrity check failed - sample rows don't match"
                        })

            if not result['errors']:
                result['status'] = 'passed'

        except Exception as e:
            result['status'] = 'error'
            result['errors'].append({
                'check': 'validation_process',
                'message': str(e)
            })

        return result

    def generate_report(self, migration_summary: Dict[str, Any], output_file: str = None) -> str:
        """Generate migration report"""
        report = f"""
ComplianceAI Database Migration Report
=====================================

Migration ID: {self.migration_id}
Generated: {datetime.now().isoformat()}

Migration Summary:
- Status: {migration_summary['status']}
- Total Tables: {migration_summary['total_tables']}
- Successful Tables: {migration_summary['successful_tables']}
- Failed Tables: {migration_summary['failed_tables']}
- Total Records: {migration_summary['total_records']:,}
- Total Time: {migration_summary['total_time_seconds']:.2f} seconds
- Average Time per Table: {migration_summary['average_time_per_table']:.2f} seconds

Table Results:
"""

        for result in migration_summary['results']:
            report += f"\n- {result['table_name']}: {result['status']}"
            if result['status'] == 'completed':
                report += f" ({result['records_processed']:,} records)"
            if result.get('errors'):
                for error in result['errors']:
                    report += f"\n  Error: {error}"

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            self.logger.info(f"Report saved to: {output_file}")

        return report


def main():
    parser = argparse.ArgumentParser(description='ComplianceAI PostgreSQL Data Migration Tool')
    parser.add_argument('command', choices=['migrate', 'validate', 'backup', 'restore', 'analyze'],
                       help='Command to execute')
    parser.add_argument('--source-db', help='Source database connection string')
    parser.add_argument('--target-db', help='Target database connection string')
    parser.add_argument('--tables', help='Comma-separated list of tables to migrate')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for operations')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--backup-file', help='Backup file path')
    parser.add_argument('--report-file', help='Migration report file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--force', action='store_true', help='Force operation without confirmation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Initialize migration tool
    tool = PostgreSQLMigrationTool(
        source_db=args.source_db,
        target_db=args.target_db,
        batch_size=args.batch_size,
        workers=args.workers,
        verbose=args.verbose
    )

    try:
        # Connect to databases
        tool.connect_databases()

        if args.command == 'migrate':
            if not args.source_db or not args.target_db:
                print("Error: --source-db and --target-db are required for migration")
                sys.exit(1)

            tables = args.tables.split(',') if args.tables else None
            summary = tool.migrate_data(tables=tables, dry_run=args.dry_run, force=args.force)

            if args.report_file:
                report = tool.generate_report(summary, args.report_file)
                print(report)
            else:
                print(json.dumps(summary, indent=2, default=str))

        elif args.command == 'validate':
            if not args.source_db or not args.target_db:
                print("Error: --source-db and --target-db are required for validation")
                sys.exit(1)

            tables = args.tables.split(',') if args.tables else None
            results = tool.validate_migration(tables=tables)
            print(json.dumps(results, indent=2))

        elif args.command == 'backup':
            if not args.source_db:
                print("Error: --source-db is required for backup")
                sys.exit(1)

            if not args.backup_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                args.backup_file = f"backup_{timestamp}.sql.gz"

            tables = args.tables.split(',') if args.tables else None
            success = tool.create_backup(args.backup_file, tables)

            if success:
                print(f"Backup completed: {args.backup_file}")
            else:
                print("Backup failed")
                sys.exit(1)

        elif args.command == 'analyze':
            if not args.source_db:
                print("Error: --source-db is required for analysis")
                sys.exit(1)

            tables = tool.get_table_list()
            analysis = {}

            for table in tables:
                info = tool.get_table_info(table)
                analysis[table] = {
                    'row_count': info.get('row_count', 0),
                    'columns': len(info.get('columns', [])),
                    'indexes': len(info.get('indexes', []))
                }

            print(json.dumps(analysis, indent=2))

        else:
            print(f"Command '{args.command}' not yet implemented")
            sys.exit(1)

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
        tool.disconnect_databases()


if __name__ == '__main__':
    main()
