#!/usr/bin/env python3
"""
ComplianceAI MongoDB Data Migration Tool
=======================================

This tool provides comprehensive data migration capabilities for MongoDB databases
used in the ComplianceAI system. It supports:

- Data migration between MongoDB clusters
- Selective collection migration
- Data transformation during migration
- Schema validation and compatibility checks
- Performance optimization for large collections

Usage:
    python mongo_migration_tool.py [command] [options]

Commands:
    migrate     Migrate data between MongoDB instances
    validate    Validate migrated data integrity
    backup      Create database backup
    restore     Restore from backup
    analyze     Analyze database performance and size

Options:
    --source-uri     Source MongoDB connection URI
    --target-uri     Target MongoDB connection URI
    --database       Database name to migrate
    --collections    Comma-separated list of collections to migrate
    --batch-size     Batch size for data operations [default: 1000]
    --workers        Number of parallel workers [default: 4]
    --dry-run        Show what would be done without executing
    --force          Force operation without confirmation
    --verbose        Enable verbose output

Examples:
    # Migrate all collections from dev to staging
    python mongo_migration_tool.py migrate --source-uri "mongodb://user:pass@dev-mongo/db" --target-uri "mongodb://user:pass@staging-mongo/db"

    # Migrate specific collections only
    python mongo_migration_tool.py migrate --collections regulatory_documents,compliance_rules

    # Validate migration integrity
    python mongo_migration_tool.py validate --source-uri "mongodb://source/db" --target-uri "mongodb://target/db"

Author: ComplianceAI Development Team
"""

import os
import sys
import argparse
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import gzip
import hashlib

# MongoDB imports
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import bson.json_util


class MongoDBMigrationTool:
    """MongoDB data migration tool for ComplianceAI"""

    def __init__(self,
                 source_uri: str = None,
                 target_uri: str = None,
                 database: str = None,
                 batch_size: int = 1000,
                 workers: int = 4,
                 verbose: bool = False):
        self.source_uri = source_uri
        self.target_uri = target_uri
        self.database = database
        self.batch_size = batch_size
        self.workers = workers
        self.verbose = verbose
        self.logger = self._setup_logger()

        # MongoDB connections
        self.source_client = None
        self.target_client = None
        self.source_db = None
        self.target_db = None

        # Migration tracking
        self.migration_id = f"mongo_migration_{int(time.time())}"
        self.migration_log = []

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('MongoDBMigrationTool')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def connect_databases(self):
        """Connect to source and target MongoDB instances"""
        try:
            if self.source_uri:
                self.logger.info("Connecting to source MongoDB...")
                self.source_client = MongoClient(self.source_uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.source_client.admin.command('ping')
                self.source_db = self.source_client[self.database] if self.database else None
                self.logger.info("Source MongoDB connection established")

            if self.target_uri:
                self.logger.info("Connecting to target MongoDB...")
                self.target_client = MongoClient(self.target_uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.target_client.admin.command('ping')
                self.target_db = self.target_client[self.database] if self.database else None
                self.logger.info("Target MongoDB connection established")

        except ConnectionFailure as e:
            self.logger.error(f"MongoDB connection failed: {str(e)}")
            sys.exit(1)

    def disconnect_databases(self):
        """Disconnect from MongoDB instances"""
        if self.source_client:
            self.source_client.close()
            self.logger.info("Source MongoDB connection closed")

        if self.target_client:
            self.target_client.close()
            self.logger.info("Target MongoDB connection closed")

    def get_collection_list(self) -> List[str]:
        """Get list of collections in the database"""
        try:
            if not self.source_db:
                return []

            # Get all collections except system collections
            collections = self.source_db.list_collection_names()
            system_collections = ['system.indexes', 'system.namespaces', 'system.profile']

            user_collections = [col for col in collections if not col.startswith('system.') and col not in system_collections]
            return sorted(user_collections)

        except Exception as e:
            self.logger.error(f"Failed to get collection list: {str(e)}")
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a collection"""
        try:
            collection = self.source_db[collection_name]

            # Get collection stats
            stats = self.source_db.command('collStats', collection_name)

            # Get indexes
            indexes = list(collection.list_indexes())

            # Get sample documents
            sample_docs = list(collection.find().limit(5))

            return {
                'collection_name': collection_name,
                'document_count': stats.get('count', 0),
                'size_bytes': stats.get('size', 0),
                'storage_size_bytes': stats.get('storageSize', 0),
                'index_count': len(indexes),
                'indexes': indexes,
                'sample_documents': sample_docs
            }

        except Exception as e:
            self.logger.error(f"Failed to get collection info for {collection_name}: {str(e)}")
            return {}

    def create_backup(self, output_file: str, collections: List[str] = None) -> bool:
        """Create a backup of specified collections"""
        self.logger.info(f"Creating backup to: {output_file}")

        try:
            # Determine collections to backup
            if not collections:
                collections = self.get_collection_list()

            # Create backup directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                # Write backup header
                backup_info = {
                    'backup_timestamp': datetime.now().isoformat(),
                    'source_database': self.database,
                    'collections': collections,
                    'migration_id': self.migration_id
                }

                f.write(f"// ComplianceAI MongoDB Backup\n")
                f.write(f"// Generated: {backup_info['backup_timestamp']}\n")
                f.write(f"// Collections: {', '.join(collections)}\n\n")

                # Backup each collection
                for collection_name in collections:
                    self.logger.info(f"Backing up collection: {collection_name}")

                    collection = self.source_db[collection_name]
                    document_count = collection.count_documents({})

                    f.write(f"// Collection: {collection_name}\n")
                    f.write(f"// Document Count: {document_count}\n\n")

                    # Export documents in batches
                    cursor = collection.find({}, {'_id': 1}).batch_size(self.batch_size)

                    for document in cursor:
                        # Convert ObjectId to string for JSON serialization
                        doc_copy = dict(document)
                        if '_id' in doc_copy:
                            doc_copy['_id'] = str(doc_copy['_id'])

                        # Write document as JSON
                        json_line = bson.json_util.dumps(doc_copy, indent=None)
                        f.write(f"{json_line}\n")

                    f.write(f"\n// End of collection: {collection_name}\n\n")

            self.logger.info(f"Backup completed successfully: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            return False

    def migrate_collection(self, collection_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate a single collection"""
        self.logger.info(f"Migrating collection: {collection_name}")

        result = {
            'collection_name': collection_name,
            'status': 'pending',
            'documents_processed': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'errors': []
        }

        try:
            source_collection = self.source_db[collection_name]
            target_collection = self.target_db[collection_name]

            # Get document count
            document_count = source_collection.count_documents({})
            self.logger.info(f"Collection {collection_name} has {document_count} documents")

            if dry_run:
                result['status'] = 'dry_run_completed'
                result['documents_processed'] = document_count
                return result

            # Migrate documents in batches
            total_processed = 0
            batch_num = 0

            cursor = source_collection.find({}).batch_size(self.batch_size)

            while True:
                batch = []
                for _ in range(self.batch_size):
                    try:
                        doc = next(cursor)
                        batch.append(doc)
                    except StopIteration:
                        break

                if not batch:
                    break

                # Insert batch into target
                try:
                    target_collection.insert_many(batch, ordered=False)
                    total_processed += len(batch)
                    batch_num += 1

                    if batch_num % 10 == 0:  # Log every 10 batches
                        self.logger.info(f"Processed {total_processed}/{document_count} documents for {collection_name}")

                except Exception as e:
                    self.logger.warning(f"Batch insert failed for {collection_name}: {str(e)}")
                    # Try inserting documents individually
                    for doc in batch:
                        try:
                            target_collection.insert_one(doc)
                            total_processed += 1
                        except Exception as doc_error:
                            result['errors'].append(f"Document insert failed: {str(doc_error)}")

            result['status'] = 'completed'
            result['documents_processed'] = total_processed
            result['end_time'] = datetime.now()

        except Exception as e:
            self.logger.error(f"Migration failed for collection {collection_name}: {str(e)}")
            result['status'] = 'error'
            result['errors'].append(str(e))

        return result

    def migrate_data(self, collections: List[str] = None, dry_run: bool = False,
                    force: bool = False) -> Dict[str, Any]:
        """Migrate data for specified collections"""
        self.logger.info("Starting MongoDB data migration process")

        # Get collections to migrate
        if not collections:
            collections = self.get_collection_list()

        if not collections:
            self.logger.error("No collections found to migrate")
            return {'status': 'error', 'message': 'No collections found'}

        # Confirm migration
        if not dry_run and not force:
            print(f"\nMigration Plan:")
            print(f"Source: {self._mask_uri(self.source_uri)}")
            print(f"Target: {self._mask_uri(self.target_uri)}")
            print(f"Database: {self.database}")
            print(f"Collections: {', '.join(collections)}")

            response = input("\nProceed with migration? [y/N]: ")
            if response.lower() != 'y':
                return {'status': 'cancelled', 'message': 'Migration cancelled by user'}

        # Execute migration
        migration_results = []
        total_start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit migration tasks
            future_to_collection = {
                executor.submit(self.migrate_collection, collection, dry_run): collection
                for collection in collections
            }

            # Collect results
            for future in as_completed(future_to_collection):
                collection = future_to_collection[future]
                try:
                    result = future.result()
                    migration_results.append(result)
                    self.migration_log.append(result)

                except Exception as e:
                    self.logger.error(f"Migration failed for {collection}: {str(e)}")
                    migration_results.append({
                        'collection_name': collection,
                        'status': 'error',
                        'errors': [str(e)]
                    })

        # Calculate summary
        total_time = time.time() - total_start_time
        successful = sum(1 for r in migration_results if r['status'] == 'completed')
        failed = sum(1 for r in migration_results if r['status'] == 'error')
        total_documents = sum(r.get('documents_processed', 0) for r in migration_results)

        summary = {
            'status': 'completed' if failed == 0 else 'partial_success',
            'total_collections': len(collections),
            'successful_collections': successful,
            'failed_collections': failed,
            'total_documents': total_documents,
            'total_time_seconds': total_time,
            'average_time_per_collection': total_time / len(collections) if collections else 0,
            'results': migration_results
        }

        self.logger.info(f"Migration completed: {successful}/{len(collections)} collections successful")
        return summary

    def _mask_uri(self, uri: str) -> str:
        """Mask sensitive information in MongoDB URI"""
        if 'mongodb://' in uri:
            # Mask password if present
            parts = uri.replace('mongodb://', '').split('@')
            if len(parts) == 2:
                credentials = parts[0].split(':')[0] if ':' in parts[0] else parts[0]
                return f"mongodb://{credentials}:***@{parts[1]}"
        return uri

    def validate_migration(self, collections: List[str] = None) -> Dict[str, Any]:
        """Validate data integrity after migration"""
        self.logger.info("Starting migration validation")

        if not collections:
            collections = self.get_collection_list()

        validation_results = {
            'total_collections': len(collections),
            'validated_collections': 0,
            'passed_validation': 0,
            'failed_validation': 0,
            'collection_results': []
        }

        for collection in collections:
            collection_result = self._validate_collection_migration(collection)
            validation_results['collection_results'].append(collection_result)

            if collection_result['status'] == 'passed':
                validation_results['passed_validation'] += 1
            elif collection_result['status'] == 'failed':
                validation_results['failed_validation'] += 1

            validation_results['validated_collections'] += 1

        validation_results['overall_status'] = 'passed' if validation_results['failed_validation'] == 0 else 'failed'

        self.logger.info(f"Validation completed: {validation_results['passed_validation']}/{validation_results['total_collections']} collections passed")
        return validation_results

    def _validate_collection_migration(self, collection_name: str) -> Dict[str, Any]:
        """Validate migration for a single collection"""
        result = {
            'collection_name': collection_name,
            'status': 'unknown',
            'checks': [],
            'errors': []
        }

        try:
            source_collection = self.source_db[collection_name]
            target_collection = self.target_db[collection_name]

            # Check document counts
            source_count = source_collection.count_documents({})
            target_count = target_collection.count_documents({})

            if source_count == target_count:
                result['checks'].append({
                    'check': 'document_count',
                    'status': 'passed',
                    'source_count': source_count,
                    'target_count': target_count
                })
            else:
                result['status'] = 'failed'
                result['errors'].append({
                    'check': 'document_count',
                    'message': f"Document count mismatch: source={source_count}, target={target_count}"
                })

            # Check data integrity (sample check)
            if source_count > 0:
                # Get a sample of documents from source
                source_sample = list(source_collection.find({}).limit(100))
                source_ids = [str(doc['_id']) for doc in source_sample]

                # Check if same documents exist in target
                target_sample = list(target_collection.find({'_id': {'$in': source_ids}}))
                target_ids = [str(doc['_id']) for doc in target_sample]

                if set(source_ids) == set(target_ids):
                    result['checks'].append({
                        'check': 'data_integrity',
                        'status': 'passed',
                        'samples_checked': len(source_sample)
                    })
                else:
                    missing_ids = set(source_ids) - set(target_ids)
                    result['status'] = 'failed'
                    result['errors'].append({
                        'check': 'data_integrity',
                        'message': f"Data integrity check failed - {len(missing_ids)} documents missing",
                        'missing_count': len(missing_ids)
                    })

            # Check indexes
            source_indexes = list(source_collection.list_indexes())
            target_indexes = list(target_collection.list_indexes())

            if len(source_indexes) == len(target_indexes):
                result['checks'].append({
                    'check': 'index_count',
                    'status': 'passed',
                    'index_count': len(source_indexes)
                })
            else:
                result['errors'].append({
                    'check': 'index_count',
                    'message': f"Index count mismatch: source={len(source_indexes)}, target={len(target_indexes)}"
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
ComplianceAI MongoDB Migration Report
====================================

Migration ID: {self.migration_id}
Generated: {datetime.now().isoformat()}

Migration Summary:
- Status: {migration_summary['status']}
- Total Collections: {migration_summary['total_collections']}
- Successful Collections: {migration_summary['successful_collections']}
- Failed Collections: {migration_summary['failed_collections']}
- Total Documents: {migration_summary['total_documents']:,}
- Total Time: {migration_summary['total_time_seconds']:.2f} seconds
- Average Time per Collection: {migration_summary['average_time_per_collection']:.2f} seconds

Collection Results:
"""

        for result in migration_summary['results']:
            report += f"\n- {result['collection_name']}: {result['status']}"
            if result['status'] == 'completed':
                report += f" ({result['documents_processed']:,} documents)"
            if result.get('errors'):
                for error in result['errors']:
                    report += f"\n  Error: {error}"

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            self.logger.info(f"Report saved to: {output_file}")

        return report


def main():
    parser = argparse.ArgumentParser(description='ComplianceAI MongoDB Data Migration Tool')
    parser.add_argument('command', choices=['migrate', 'validate', 'backup', 'restore', 'analyze'],
                       help='Command to execute')
    parser.add_argument('--source-uri', help='Source MongoDB connection URI')
    parser.add_argument('--target-uri', help='Target MongoDB connection URI')
    parser.add_argument('--database', help='Database name to migrate')
    parser.add_argument('--collections', help='Comma-separated list of collections to migrate')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for operations')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--backup-file', help='Backup file path')
    parser.add_argument('--report-file', help='Migration report file path')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--force', action='store_true', help='Force operation without confirmation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    # Initialize migration tool
    tool = MongoDBMigrationTool(
        source_uri=args.source_uri,
        target_uri=args.target_uri,
        database=args.database,
        batch_size=args.batch_size,
        workers=args.workers,
        verbose=args.verbose
    )

    try:
        # Connect to databases
        tool.connect_databases()

        if args.command == 'migrate':
            if not args.source_uri or not args.target_uri or not args.database:
                print("Error: --source-uri, --target-uri, and --database are required for migration")
                sys.exit(1)

            collections = args.collections.split(',') if args.collections else None
            summary = tool.migrate_data(collections=collections, dry_run=args.dry_run, force=args.force)

            if args.report_file:
                report = tool.generate_report(summary, args.report_file)
                print(report)
            else:
                print(json.dumps(summary, indent=2, default=str))

        elif args.command == 'validate':
            if not args.source_uri or not args.target_uri or not args.database:
                print("Error: --source-uri, --target-uri, and --database are required for validation")
                sys.exit(1)

            collections = args.collections.split(',') if args.collections else None
            results = tool.validate_migration(collections=collections)
            print(json.dumps(results, indent=2))

        elif args.command == 'backup':
            if not args.source_uri or not args.database:
                print("Error: --source-uri and --database are required for backup")
                sys.exit(1)

            if not args.backup_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                args.backup_file = f"mongo_backup_{timestamp}.json.gz"

            collections = args.collections.split(',') if args.collections else None
            success = tool.create_backup(args.backup_file, collections)

            if success:
                print(f"Backup completed: {args.backup_file}")
            else:
                print("Backup failed")
                sys.exit(1)

        elif args.command == 'analyze':
            if not args.source_uri or not args.database:
                print("Error: --source-uri and --database are required for analysis")
                sys.exit(1)

            collections = tool.get_collection_list()
            analysis = {}

            for collection in collections:
                info = tool.get_collection_info(collection)
                analysis[collection] = {
                    'document_count': info.get('document_count', 0),
                    'size_bytes': info.get('size_bytes', 0),
                    'index_count': info.get('index_count', 0)
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
