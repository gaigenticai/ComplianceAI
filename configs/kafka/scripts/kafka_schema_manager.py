#!/usr/bin/env python3
"""
ComplianceAI Kafka Schema Manager
=================================

This script manages Kafka schemas and topics for the ComplianceAI system.
It provides functionality to:
- Register schemas with Schema Registry
- Create Kafka topics
- Validate schema compatibility
- Manage schema versions
- Generate schema documentation

Usage:
    python kafka_schema_manager.py [command] [options]

Commands:
    register    Register schemas with Schema Registry
    create      Create Kafka topics
    validate    Validate schemas and topics
    list        List registered schemas and topics
    delete      Delete schemas or topics
    export      Export schemas and topic configurations

Options:
    --schema-registry-url    Schema Registry URL [default: http://localhost:8081]
    --kafka-bootstrap        Kafka bootstrap servers [default: localhost:9092]
    --config-dir             Configuration directory [default: ./configs/kafka]
    --dry-run                Show what would be done without executing
    --force                  Force operation without confirmation
    --verbose                Enable verbose output

Examples:
    # Register all schemas
    python kafka_schema_manager.py register

    # Create all topics
    python kafka_schema_manager.py create

    # Validate configuration
    python kafka_schema_manager.py validate

    # List all schemas
    python kafka_schema_manager.py list schemas

Author: ComplianceAI Development Team
"""

import os
import sys
import json
import argparse
import requests
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

# Kafka and Schema Registry imports
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource
from confluent_kafka import KafkaException
import avro.schema


class KafkaSchemaManager:
    """Kafka Schema and Topic Manager for ComplianceAI"""

    def __init__(self,
                 schema_registry_url: str = 'http://localhost:8081',
                 kafka_bootstrap: str = 'localhost:9092',
                 config_dir: str = './configs/kafka',
                 verbose: bool = False):
        self.schema_registry_url = schema_registry_url.rstrip('/')
        self.kafka_bootstrap = kafka_bootstrap
        self.config_dir = Path(config_dir)
        self.verbose = verbose
        self.logger = self._setup_logger()

        # Initialize Kafka admin client
        self.admin_client = AdminClient({
            'bootstrap.servers': kafka_bootstrap,
            'client.id': 'kafka-schema-manager'
        })

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('KafkaSchemaManager')
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _make_schema_registry_request(self,
                                    method: str,
                                    endpoint: str,
                                    data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to Schema Registry"""
        url = f"{self.schema_registry_url}{endpoint}"
        headers = {'Content-Type': 'application/vnd.schemaregistry.v1+json'}

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json() if response.content else {}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Schema Registry request failed: {str(e)}")
            raise

    def register_schema(self, subject: str, schema_file: Path, schema_type: str = 'AVRO') -> Dict:
        """Register a schema with Schema Registry"""
        self.logger.info(f"Registering schema: {subject} from {schema_file}")

        try:
            # Read schema file
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_str = f.read()

            # Validate Avro schema
            if schema_type.upper() == 'AVRO':
                avro.schema.Parse(schema_str)

            # Prepare registration data
            data = {
                'schema': schema_str,
                'schemaType': schema_type,
                'references': []
            }

            # Register schema
            result = self._make_schema_registry_request(
                'POST',
                f'/subjects/{subject}/versions',
                data
            )

            self.logger.info(f"Successfully registered schema: {subject} (ID: {result.get('id')})")
            return result

        except Exception as e:
            self.logger.error(f"Failed to register schema {subject}: {str(e)}")
            raise

    def create_topic(self, topic_config: Dict) -> None:
        """Create a Kafka topic"""
        topic_name = topic_config['name']
        self.logger.info(f"Creating topic: {topic_name}")

        try:
            # Prepare topic configuration
            topic = NewTopic(
                topic=topic_name,
                num_partitions=topic_config['partitions'],
                replication_factor=topic_config['replication_factor'],
                config=topic_config.get('config', {})
            )

            # Create topic
            futures = self.admin_client.create_topics([topic])

            # Wait for operation to complete
            for topic_name_future, future in futures.items():
                future.result(timeout=30)
                self.logger.info(f"Successfully created topic: {topic_name_future}")

        except KafkaException as e:
            self.logger.error(f"Failed to create topic {topic_name}: {str(e)}")
            raise

    def validate_schema(self, schema_file: Path, schema_type: str = 'AVRO') -> bool:
        """Validate schema syntax"""
        self.logger.info(f"Validating schema: {schema_file}")

        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_str = f.read()

            if schema_type.upper() == 'AVRO':
                avro.schema.Parse(schema_str)

            self.logger.info(f"Schema validation successful: {schema_file}")
            return True

        except Exception as e:
            self.logger.error(f"Schema validation failed for {schema_file}: {str(e)}")
            return False

    def check_topic_exists(self, topic_name: str) -> bool:
        """Check if a Kafka topic exists"""
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            return topic_name in metadata.topics
        except KafkaException as e:
            self.logger.error(f"Failed to check topic existence: {str(e)}")
            return False

    def get_registered_schemas(self) -> List[Dict]:
        """Get list of registered schemas"""
        try:
            subjects = self._make_schema_registry_request('GET', '/subjects')
            schemas = []

            for subject in subjects:
                versions = self._make_schema_registry_request(
                    'GET',
                    f'/subjects/{subject}/versions'
                )

                for version in versions:
                    schema_info = self._make_schema_registry_request(
                        'GET',
                        f'/subjects/{subject}/versions/{version}'
                    )
                    schemas.append({
                        'subject': subject,
                        'version': version,
                        'schema': schema_info
                    })

            return schemas

        except Exception as e:
            self.logger.error(f"Failed to get registered schemas: {str(e)}")
            return []

    def get_topics(self) -> List[str]:
        """Get list of Kafka topics"""
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            return list(metadata.topics.keys())
        except KafkaException as e:
            self.logger.error(f"Failed to get topics: {str(e)}")
            return []

    def load_topic_configurations(self) -> List[Dict]:
        """Load topic configurations from JSON file"""
        topics_file = self.config_dir / 'topics' / 'topics.json'

        if not topics_file.exists():
            raise FileNotFoundError(f"Topics configuration file not found: {topics_file}")

        with open(topics_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return config.get('topics', [])

    def register_all_schemas(self, dry_run: bool = False, force: bool = False) -> bool:
        """Register all schemas defined in topic configurations"""
        self.logger.info("Starting schema registration process")

        try:
            topic_configs = self.load_topic_configurations()
            success = True

            for topic_config in topic_configs:
                if 'schema' in topic_config:
                    schema_config = topic_config['schema']
                    schema_file = self.config_dir / schema_config['schema_file']

                    if not schema_file.exists():
                        self.logger.warning(f"Schema file not found: {schema_file}")
                        if not force:
                            success = False
                            continue

                    subject = schema_config['subject']
                    schema_type = schema_config.get('schema_type', 'AVRO')

                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would register schema: {subject} from {schema_file}")
                        continue

                    try:
                        self.register_schema(subject, schema_file, schema_type)
                    except Exception as e:
                        self.logger.error(f"Failed to register schema {subject}: {str(e)}")
                        if not force:
                            success = False

            return success

        except Exception as e:
            self.logger.error(f"Schema registration process failed: {str(e)}")
            return False

    def create_all_topics(self, dry_run: bool = False, force: bool = False) -> bool:
        """Create all topics defined in topic configurations"""
        self.logger.info("Starting topic creation process")

        try:
            topic_configs = self.load_topic_configurations()
            success = True

            for topic_config in topic_configs:
                topic_name = topic_config['name']

                if dry_run:
                    self.logger.info(f"[DRY RUN] Would create topic: {topic_name}")
                    continue

                # Check if topic already exists
                if self.check_topic_exists(topic_name):
                    self.logger.info(f"Topic already exists: {topic_name}")
                    continue

                try:
                    self.create_topic(topic_config)
                except Exception as e:
                    self.logger.error(f"Failed to create topic {topic_name}: {str(e)}")
                    if not force:
                        success = False

            return success

        except Exception as e:
            self.logger.error(f"Topic creation process failed: {str(e)}")
            return False

    def validate_all_schemas(self) -> Dict[str, Any]:
        """Validate all schema files"""
        self.logger.info("Starting schema validation process")

        validation_results = {
            'total_schemas': 0,
            'valid_schemas': 0,
            'invalid_schemas': 0,
            'errors': []
        }

        try:
            topic_configs = self.load_topic_configurations()

            for topic_config in topic_configs:
                if 'schema' in topic_config:
                    schema_config = topic_config['schema']
                    schema_file = self.config_dir / schema_config['schema_file']

                    validation_results['total_schemas'] += 1

                    if not schema_file.exists():
                        error = f"Schema file not found: {schema_file}"
                        self.logger.error(error)
                        validation_results['errors'].append(error)
                        validation_results['invalid_schemas'] += 1
                        continue

                    schema_type = schema_config.get('schema_type', 'AVRO')
                    if self.validate_schema(schema_file, schema_type):
                        validation_results['valid_schemas'] += 1
                    else:
                        validation_results['invalid_schemas'] += 1

            return validation_results

        except Exception as e:
            self.logger.error(f"Schema validation process failed: {str(e)}")
            validation_results['errors'].append(str(e))
            return validation_results

    def list_schemas_and_topics(self) -> Dict[str, Any]:
        """List all registered schemas and topics"""
        return {
            'registered_schemas': self.get_registered_schemas(),
            'topics': self.get_topics()
        }

    def export_configuration(self, output_dir: str) -> None:
        """Export current schema and topic configurations"""
        self.logger.info(f"Exporting configuration to: {output_dir}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export registered schemas
        schemas = self.get_registered_schemas()
        with open(output_path / 'registered_schemas.json', 'w') as f:
            json.dump(schemas, f, indent=2)

        # Export topics
        topics = self.get_topics()
        with open(output_path / 'topics.json', 'w') as f:
            json.dump({'topics': topics}, f, indent=2)

        # Export topic configurations
        try:
            topic_configs = self.load_topic_configurations()
            with open(output_path / 'topic_configs.json', 'w') as f:
                json.dump(topic_configs, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not export topic configurations: {str(e)}")

        self.logger.info("Configuration export completed")


def main():
    parser = argparse.ArgumentParser(description='ComplianceAI Kafka Schema Manager')
    parser.add_argument('command', choices=[
        'register', 'create', 'validate', 'list', 'delete', 'export'
    ], help='Command to execute')
    parser.add_argument('--schema-registry-url', default='http://localhost:8081',
                       help='Schema Registry URL')
    parser.add_argument('--kafka-bootstrap', default='localhost:9092',
                       help='Kafka bootstrap servers')
    parser.add_argument('--config-dir', default='./configs/kafka',
                       help='Configuration directory')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--force', action='store_true',
                       help='Force operation without confirmation')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--output-dir', default='./export',
                       help='Output directory for export command')

    args = parser.parse_args()

    # Initialize schema manager
    manager = KafkaSchemaManager(
        schema_registry_url=args.schema_registry_url,
        kafka_bootstrap=args.kafka_bootstrap,
        config_dir=args.config_dir,
        verbose=args.verbose
    )

    try:
        if args.command == 'register':
            success = manager.register_all_schemas(
                dry_run=args.dry_run,
                force=args.force
            )
            if not success:
                sys.exit(1)

        elif args.command == 'create':
            success = manager.create_all_topics(
                dry_run=args.dry_run,
                force=args.force
            )
            if not success:
                sys.exit(1)

        elif args.command == 'validate':
            results = manager.validate_all_schemas()
            print(json.dumps(results, indent=2))

            if results['invalid_schemas'] > 0:
                sys.exit(1)

        elif args.command == 'list':
            info = manager.list_schemas_and_topics()
            print(json.dumps(info, indent=2))

        elif args.command == 'export':
            manager.export_configuration(args.output_dir)

        elif args.command == 'delete':
            print("Delete functionality not yet implemented")
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


if __name__ == '__main__':
    main()
