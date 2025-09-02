# Kafka Schema Registry Setup and Management

This directory contains Kafka schema definitions, topic configurations, and management tools for the ComplianceAI system.

## Directory Structure

```
kafka/
├── schemas/                    # Avro schema definitions
│   ├── regulatory_update.avsc
│   ├── compliance_event.avsc
│   ├── data_processing_event.avsc
│   └── system_metrics.avsc
├── topics/                     # Topic configurations
│   └── topics.json
├── registry/                   # Schema Registry configuration
│   └── schema-registry.properties
└── scripts/                    # Management scripts
    └── kafka_schema_manager.py
```

## Schema Definitions

### Regulatory Update Schema (`regulatory_update.avsc`)
- **Purpose**: Schema for regulatory document updates and changes
- **Key Fields**:
  - `event_id`: Unique identifier for the regulatory update event
  - `document_id`: Reference to the regulatory document
  - `jurisdiction`: Regulatory jurisdiction (EU, UK, US, etc.)
  - `document_type`: Type of regulatory document
  - `effective_date`: When the change becomes effective
  - `impact_level`: Business impact level of the change

### Compliance Event Schema (`compliance_event.avsc`)
- **Purpose**: Schema for compliance-related events and activities
- **Key Fields**:
  - `event_type`: Type of compliance event (report_generated, validation_failed, etc.)
  - `entity_type`: Type of entity involved (report, requirement, institution)
  - `severity`: Event severity level
  - `event_data`: Structured event data with specific information

### Data Processing Event Schema (`data_processing_event.avsc`)
- **Purpose**: Schema for data processing events and status updates
- **Key Fields**:
  - `processing_type`: Type of data processing operation
  - `record_count`: Number of records processed
  - `processing_status`: Current processing status
  - `processing_metrics`: Detailed performance metrics
  - `data_quality_metrics`: Data quality assessment results

### System Metrics Schema (`system_metrics.avsc`)
- **Purpose**: Schema for system performance and health metrics
- **Key Fields**:
  - `service_name`: Name of the service reporting metrics
  - `metric_type`: Category of metrics (system, application, business)
  - `system_metrics`: System-level performance data
  - `application_metrics`: Application-specific metrics
  - `business_metrics`: Business-level KPIs

## Topic Configurations

The `topics.json` file defines all Kafka topics used by ComplianceAI:

### Core Topics

1. **regulatory-updates**
   - **Purpose**: Regulatory document updates and changes
   - **Partitions**: 3
   - **Retention**: 7 days
   - **Consumers**: Regulatory Intelligence, Intelligence & Compliance, Decision & Orchestration

2. **compliance-events**
   - **Purpose**: Compliance-related events and activities
   - **Partitions**: 6
   - **Retention**: 30 days
   - **Consumers**: Intelligence & Compliance, Decision & Orchestration, Monitoring

3. **data-processing-events**
   - **Purpose**: Data processing events and status updates
   - **Partitions**: 4
   - **Retention**: 7 days
   - **Consumers**: Monitoring, Reporting

4. **system-metrics**
   - **Purpose**: System performance and health metrics
   - **Partitions**: 2
   - **Retention**: 3 days
   - **Consumers**: Monitoring, Alerting

### Command and Status Topics

5. **report-commands**
   - **Purpose**: Report generation and processing commands
   - **Partitions**: 3
   - **Retention**: 1 day

6. **report-status-updates**
   - **Purpose**: Report generation status updates
   - **Partitions**: 4
   - **Retention**: 30 days

### Audit and Monitoring Topics

7. **audit-events**
   - **Purpose**: Security and audit events
   - **Partitions**: 5
   - **Retention**: 1 year

8. **error-events**
   - **Purpose**: Application errors and exceptions
   - **Partitions**: 3
   - **Retention**: 7 days

9. **data-quality-events**
   - **Purpose**: Data quality assessment results
   - **Partitions**: 2
   - **Retention**: 30 days

10. **workflow-events**
    - **Purpose**: Workflow execution events
    - **Partitions**: 3
    - **Retention**: 30 days

## Schema Registry Setup

### Prerequisites

- Confluent Platform or Apache Kafka with Schema Registry
- Java 8+
- Kafka cluster running

### Installation

1. **Download Schema Registry**:
   ```bash
   wget https://packages.confluent.io/archive/7.4/confluent-7.4.0.tar.gz
   tar -xzf confluent-7.4.0.tar.gz
   cd confluent-7.4.0
   ```

2. **Configure Schema Registry**:
   ```bash
   cp etc/schema-registry/schema-registry.properties etc/schema-registry/schema-registry.properties.backup
   cp /path/to/complianceai/configs/kafka/registry/schema-registry.properties etc/schema-registry/schema-registry.properties
   ```

3. **Update Configuration**:
   Edit `schema-registry.properties` to match your environment:
   ```properties
   kafkastore.bootstrap.servers=your-kafka-bootstrap-servers
   schema.registry.host.name=your-schema-registry-host
   ```

4. **Start Schema Registry**:
   ```bash
   ./bin/schema-registry-start etc/schema-registry/schema-registry.properties
   ```

5. **Verify Installation**:
   ```bash
   curl http://localhost:8081/subjects
   ```

### Docker Setup

```yaml
version: '3.8'
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:7.4.0
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
    depends_on:
      - kafka
```

## Using the Schema Manager

The `kafka_schema_manager.py` script provides comprehensive schema and topic management.

### Prerequisites

Install required Python packages:
```bash
pip install confluent-kafka requests avro-python3
```

### Commands

#### Register Schemas
```bash
# Register all schemas with Schema Registry
python kafka_schema_manager.py register

# Register schemas with custom Schema Registry URL
python kafka_schema_manager.py register --schema-registry-url http://schema-registry:8081

# Dry run (show what would be done)
python kafka_schema_manager.py register --dry-run
```

#### Create Topics
```bash
# Create all topics defined in topics.json
python kafka_schema_manager.py create

# Create topics with custom Kafka bootstrap servers
python kafka_schema_manager.py create --kafka-bootstrap kafka:9092

# Dry run
python kafka_schema_manager.py create --dry-run
```

#### Validate Configuration
```bash
# Validate all schemas and topic configurations
python kafka_schema_manager.py validate

# Validate with verbose output
python kafka_schema_manager.py validate --verbose
```

#### List Schemas and Topics
```bash
# List all registered schemas
python kafka_schema_manager.py list

# List with detailed information
python kafka_schema_manager.py list --verbose
```

#### Export Configuration
```bash
# Export current schema and topic configurations
python kafka_schema_manager.py export --output-dir ./export

# Export to specific directory
python kafka_schema_manager.py export --output-dir /path/to/backup
```

### Advanced Options

#### Custom Configuration Directory
```bash
# Use custom configuration directory
python kafka_schema_manager.py register --config-dir /path/to/custom/config
```

#### Force Operations
```bash
# Force operations without confirmation prompts
python kafka_schema_manager.py create --force
```

#### Verbose Logging
```bash
# Enable verbose logging for all commands
python kafka_schema_manager.py validate --verbose
```

## Schema Compatibility

### Compatibility Levels

Schema Registry supports different compatibility levels:

- **BACKWARD**: New schema can read data written by old schema
- **FORWARD**: Old schema can read data written by new schema
- **FULL**: Both backward and forward compatibility
- **NONE**: No compatibility checks

### Setting Compatibility

```bash
# Set global compatibility level
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "BACKWARD"}' \
  http://localhost:8081/config

# Set compatibility for specific subject
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FULL"}' \
  http://localhost:8081/config/regulatory-updates-value
```

### Compatibility Validation

The schema manager automatically validates compatibility when registering new schema versions:

```python
# Check compatibility before registration
python kafka_schema_manager.py validate --compatibility-check
```

## Topic Management

### Topic Configuration

Topics are configured with the following parameters:

- **partitions**: Number of partitions for parallelism
- **replication_factor**: Number of replicas for fault tolerance
- **retention**: How long to retain messages
- **cleanup.policy**: Message cleanup policy (delete, compact)
- **compression**: Message compression type

### Monitoring Topics

```bash
# Check topic status
kafka-topics --bootstrap-server localhost:9092 --describe --topic regulatory-updates

# Monitor topic lag
kafka-consumer-groups --bootstrap-server localhost:9092 --group compliance-group --describe
```

### Topic Maintenance

```bash
# Increase partitions
kafka-topics --bootstrap-server localhost:9092 --alter --topic regulatory-updates --partitions 6

# Change retention
kafka-configs --bootstrap-server localhost:9092 --alter --entity-type topics --entity-name regulatory-updates --add-config retention.ms=1209600000
```

## Schema Evolution

### Adding New Schema Versions

1. **Create new schema file**:
   ```bash
   cp schemas/regulatory_update.avsc schemas/regulatory_update_v2.avsc
   # Edit v2 schema with new fields
   ```

2. **Update topic configuration**:
   ```json
   {
     "schema": {
       "subject": "regulatory-updates-value",
       "schema_file": "schemas/regulatory_update_v2.avsc",
       "schema_type": "AVRO"
     }
   }
   ```

3. **Register new version**:
   ```bash
   python kafka_schema_manager.py register
   ```

### Schema Migration Strategy

1. **Backward Compatible Changes**:
   - Add optional fields with defaults
   - Add new enum values
   - Add new union types

2. **Breaking Changes**:
   - Remove required fields
   - Change field types
   - Rename fields

3. **Migration Process**:
   - Update consumer applications
   - Deploy new schema version
   - Monitor for compatibility issues
   - Rollback if necessary

## Error Handling

### Common Issues

#### Schema Registration Failures

**Compatibility Error**:
```
Schema being registered is incompatible with an earlier schema
```
**Solution**: Review compatibility requirements and adjust schema or compatibility level

**Invalid Schema**:
```
Invalid Avro schema
```
**Solution**: Validate schema syntax using `python kafka_schema_manager.py validate`

#### Topic Creation Failures

**Insufficient Replicas**:
```
replication factor larger than available brokers
```
**Solution**: Reduce replication factor or add more Kafka brokers

**Invalid Configuration**:
```
Invalid config value
```
**Solution**: Check topic configuration values against Kafka documentation

### Troubleshooting

#### Check Schema Registry Health

```bash
# Health check
curl http://localhost:8081/subjects

# Detailed health
curl http://localhost:8081/v1/metadata/id,version,commitref
```

#### Validate Schema Registration

```bash
# List registered schemas
curl http://localhost:8081/subjects

# Get schema versions
curl http://localhost:8081/subjects/regulatory-updates-value/versions

# Get latest schema
curl http://localhost:8081/subjects/regulatory-updates-value/versions/latest
```

#### Debug Kafka Connections

```bash
# Test Kafka connectivity
kafka-console-producer --bootstrap-server localhost:9092 --topic test

# Check broker status
zookeeper-shell localhost:2181 ls /brokers/ids
```

## Best Practices

### Schema Design

1. **Use meaningful names**: Choose descriptive field names
2. **Provide documentation**: Add doc strings to schemas
3. **Use appropriate types**: Choose correct Avro data types
4. **Plan for evolution**: Design schemas with future changes in mind
5. **Validate thoroughly**: Test schemas with sample data

### Topic Configuration

1. **Right-size partitions**: Balance parallelism and overhead
2. **Set appropriate retention**: Balance storage costs and data needs
3. **Configure compression**: Use compression for large messages
4. **Monitor performance**: Track throughput and latency
5. **Plan for growth**: Design for future scaling needs

### Operational Practices

1. **Version control**: Keep schemas in version control
2. **Test changes**: Validate changes in staging environment
3. **Monitor compatibility**: Track schema compatibility issues
4. **Document changes**: Maintain changelog for schema changes
5. **Backup configurations**: Regularly backup schema and topic configurations

## Integration Examples

### Producer Example (Python)

```python
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Initialize Schema Registry client
schema_registry_client = SchemaRegistryClient({
    'url': 'http://localhost:8081'
})

# Load schema
with open('schemas/regulatory_update.avsc', 'r') as f:
    schema_str = f.read()

# Create Avro serializer
serializer = AvroSerializer(
    schema_registry_client,
    schema_str,
    lambda obj, ctx: obj  # to_dict function
)

# Create producer
producer = Producer({
    'bootstrap.servers': 'localhost:9092'
})

# Produce message
regulatory_update = {
    'event_id': 'event-123',
    'document_id': 'doc-456',
    'jurisdiction': 'EU',
    'title': 'New Regulatory Requirement',
    'effective_date': 1640995200000,  # timestamp
    'impact_level': 'medium'
}

producer.produce(
    topic='regulatory-updates',
    value=serializer(regulatory_update, SerializationContext('regulatory-updates', MessageField.VALUE)),
    on_delivery=delivery_report
)
```

### Consumer Example (Python)

```python
from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Initialize Schema Registry client
schema_registry_client = SchemaRegistryClient({
    'url': 'http://localhost:8081'
})

# Load schema
with open('schemas/regulatory_update.avsc', 'r') as f:
    schema_str = f.read()

# Create Avro deserializer
deserializer = AvroDeserializer(
    schema_registry_client,
    schema_str,
    lambda obj, ctx: obj  # from_dict function
)

# Create consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'compliance-consumer',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['regulatory-updates'])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(f"Consumer error: {msg.error()}")
        continue

    # Deserialize message
    regulatory_update = deserializer(
        msg.value(),
        SerializationContext(msg.topic(), MessageField.VALUE)
    )

    print(f"Received regulatory update: {regulatory_update}")
```

## Security Considerations

### Schema Registry Security

1. **Authentication**: Enable authentication for Schema Registry
2. **Authorization**: Configure role-based access control
3. **TLS Encryption**: Use TLS for all communications
4. **Audit Logging**: Enable comprehensive audit logging

### Kafka Security

1. **SSL/TLS**: Enable encryption for Kafka communications
2. **SASL Authentication**: Use SASL for client authentication
3. **ACLs**: Configure topic-level access controls
4. **Encryption at Rest**: Enable data encryption for Kafka storage

### Monitoring and Alerting

1. **Schema Registry Metrics**: Monitor schema registration rates
2. **Kafka Metrics**: Track topic throughput and lag
3. **Error Monitoring**: Alert on schema compatibility issues
4. **Performance Monitoring**: Monitor serialization/deserialization performance

## Support and Resources

- **Confluent Documentation**: Official Schema Registry and Kafka documentation
- **Avro Specification**: Apache Avro schema specification
- **Kafka Documentation**: Apache Kafka documentation
- **Community Support**: Kafka and Schema Registry user communities

## Version History

- **v1.0**: Initial schema definitions and topic configurations
- **v1.1**: Added comprehensive schema management tools
- **v1.2**: Enhanced monitoring and alerting capabilities
- **v1.3**: Added security hardening and compliance features
