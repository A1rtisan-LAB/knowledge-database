# 🔧 Knowledge Database Administrator Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [User Management](#user-management)
3. [Content Administration](#content-administration)
4. [System Configuration](#system-configuration)
5. [Monitoring and Analytics](#monitoring-and-analytics)
6. [Backup and Recovery](#backup-and-recovery)
7. [Performance Tuning](#performance-tuning)
8. [Security Management](#security-management)
9. [Troubleshooting](#troubleshooting)

## System Overview

### Architecture Components
- **Application Server**: FastAPI on Gunicorn
- **Database**: PostgreSQL with pgvector extension
- **Search Engine**: OpenSearch for full-text and vector search
- **Cache Layer**: Redis for session and data caching
- **Load Balancer**: Nginx reverse proxy
- **Container Platform**: Docker with Docker Compose

### Access Levels
1. **Super Admin**: Full system access
2. **Admin**: User and content management
3. **Moderator**: Content review and approval
4. **Editor**: Content creation and editing
5. **Viewer**: Read-only access

## User Management

### Creating Users
```bash
# Via Admin API
POST /api/v1/admin/users
{
  "email": "user@example.com",
  "username": "johndoe",
  "role": "editor",
  "department": "Engineering"
}
```

### Bulk User Import
1. Prepare CSV file with user data
2. Navigate to Admin Panel → Users → Import
3. Upload CSV file
4. Review and confirm import
5. Users receive activation emails

### Managing Permissions
- **Role Assignment**: Admin Panel → Users → Edit → Role
- **Department Access**: Configure department-based permissions
- **API Access**: Generate and manage API tokens
- **Rate Limits**: Set per-user or per-role limits

### User Activity Monitoring
- View login history
- Track content contributions
- Monitor API usage
- Export activity reports

## Content Administration

### Content Moderation
1. **Review Queue**: Admin Panel → Moderation
2. **Actions Available**:
   - Approve for publication
   - Request changes
   - Reject with reason
   - Flag for escalation

### Category Management
```python
# Category Structure
- Technology
  ├── Software Development
  │   ├── Backend
  │   ├── Frontend
  │   └── DevOps
  └── Data Science
      ├── Machine Learning
      └── Analytics
```

### Bulk Operations
- **Import Content**: Support for JSON, CSV, Markdown
- **Export Data**: Full or filtered exports
- **Mass Updates**: Batch category changes, tag updates
- **Cleanup Tasks**: Remove duplicates, fix broken links

### Content Quality Control
- Set minimum content length
- Configure required metadata fields
- Enable plagiarism detection
- Implement approval workflows

## System Configuration

### Environment Variables
```bash
# Core Settings
APP_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/kb
REDIS_URL=redis://localhost:6379
OPENSEARCH_URL=http://localhost:9200

# Performance
MAX_CONNECTIONS=100
WORKER_COUNT=4
REQUEST_TIMEOUT=30

# Security
JWT_EXPIRY=3600
RATE_LIMIT=100
CORS_ORIGINS=https://your-domain.com
```

### Database Configuration
```sql
-- Optimize PostgreSQL
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET random_page_cost = 1.1;
```

### Search Engine Tuning
```json
// OpenSearch settings
{
  "index": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "30s"
  },
  "analysis": {
    "analyzer": {
      "korean_analyzer": {
        "type": "custom",
        "tokenizer": "nori_tokenizer"
      }
    }
  }
}
```

## Monitoring and Analytics

### System Metrics
- **Dashboard URL**: http://localhost:3000/grafana
- **Key Metrics**:
  - Request rate and latency
  - Database query performance
  - Cache hit ratio
  - Search response times
  - Error rates

### Application Logs
```bash
# View application logs
docker logs kb-app-prod -f

# Search specific errors
docker logs kb-app-prod 2>&1 | grep ERROR

# Export logs
docker logs kb-app-prod > app_logs_$(date +%Y%m%d).log
```

### Usage Analytics
- Most searched terms
- Popular content
- User engagement metrics
- Content creation trends
- API usage patterns

### Alerts Configuration
```yaml
# Alert rules (Prometheus)
groups:
  - name: knowledge_db
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
      - alert: DatabaseDown
        expr: up{job="postgresql"} == 0
      - alert: LowDiskSpace
        expr: disk_free_percent < 10
```

## Backup and Recovery

### Automated Backups
```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U kb_user knowledge_db > $BACKUP_DIR/database.sql

# OpenSearch snapshot
curl -X PUT "localhost:9200/_snapshot/backup/$(date +%Y%m%d)?wait_for_completion=true"

# Redis backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/

# Compress and encrypt
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
gpg --encrypt --recipient admin@example.com $BACKUP_DIR.tar.gz
```

### Recovery Procedures
1. **Database Recovery**:
   ```bash
   psql -h localhost -U kb_user knowledge_db < backup.sql
   ```

2. **Search Index Recovery**:
   ```bash
   curl -X POST "localhost:9200/_snapshot/backup/20250821/_restore"
   ```

3. **Full System Recovery**:
   - Stop all services
   - Restore database
   - Restore search indices
   - Restore Redis data
   - Restart services
   - Verify functionality

## Performance Tuning

### Database Optimization
- **Indexing Strategy**:
  ```sql
  CREATE INDEX idx_items_created ON knowledge_items(created_at);
  CREATE INDEX idx_items_category ON knowledge_items(category_id);
  CREATE INDEX idx_search_vector ON knowledge_items USING ivfflat (embedding);
  ```

- **Query Optimization**:
  - Use EXPLAIN ANALYZE for slow queries
  - Implement query result caching
  - Optimize JOIN operations
  - Regular VACUUM and ANALYZE

### Caching Strategy
```python
# Redis caching configuration
CACHE_TTL = {
    'search_results': 300,  # 5 minutes
    'user_sessions': 3600,  # 1 hour
    'static_content': 86400, # 24 hours
    'api_responses': 60     # 1 minute
}
```

### Resource Scaling
- **Horizontal Scaling**: Add more application containers
- **Vertical Scaling**: Increase memory/CPU allocations
- **Load Balancing**: Configure Nginx upstream servers
- **CDN Integration**: Offload static assets

## Security Management

### Security Checklist
- [ ] Strong passwords enforced
- [ ] Two-factor authentication enabled
- [ ] SSL/TLS certificates valid
- [ ] Regular security updates applied
- [ ] Firewall rules configured
- [ ] Rate limiting active
- [ ] Input validation enabled
- [ ] SQL injection prevention
- [ ] XSS protection configured
- [ ] CORS properly set

### Access Control
```python
# Role-based permissions
PERMISSIONS = {
    'super_admin': ['*'],
    'admin': ['user:*', 'content:*', 'analytics:view'],
    'moderator': ['content:review', 'content:approve'],
    'editor': ['content:create', 'content:edit', 'content:delete'],
    'viewer': ['content:view', 'search:*']
}
```

### Audit Logging
- All admin actions logged
- User authentication events
- Content modifications tracked
- API access recorded
- Security events monitored

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
docker stats

# Restart specific service
docker-compose restart opensearch

# Clear caches
redis-cli FLUSHDB
```

#### Slow Search Performance
1. Check OpenSearch cluster health
2. Optimize index settings
3. Review query complexity
4. Increase heap size if needed

#### Database Connection Issues
```bash
# Test connection
psql -h localhost -U kb_user -d knowledge_db -c "SELECT 1"

# Check connection pool
SELECT count(*) FROM pg_stat_activity;

# Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND state_change < now() - interval '1 hour';
```

### Emergency Procedures

#### System Recovery
1. Check service status
2. Review error logs
3. Restart failed services
4. Verify database connectivity
5. Test search functionality
6. Confirm user access

#### Data Corruption
1. Stop affected services
2. Restore from latest backup
3. Verify data integrity
4. Reindex search data if needed
5. Clear corrupted caches

### Support Escalation
1. **Level 1**: System alerts and monitoring
2. **Level 2**: Admin team investigation
3. **Level 3**: Development team engagement
4. **Critical**: Emergency response team

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Emergency Contact**: ops@your-domain.com  
**Documentation**: https://docs.your-domain.com