# 📚 Knowledge Database User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Searching for Knowledge](#searching-for-knowledge)
3. [Creating Knowledge Items](#creating-knowledge-items)
4. [Managing Your Content](#managing-your-content)
5. [Collaboration Features](#collaboration-features)
6. [Advanced Features](#advanced-features)
7. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### System Access

#### Running the Application
The Knowledge Database can be run in two modes:

**Foreground Mode** (Default):
```bash
./scripts/start-local.sh
# Application runs in current terminal
# Logs displayed in console
# Use Ctrl+C to stop
```

**Background Mode** (Recommended for Development):
```bash
./scripts/start-local.sh --background
# Application runs in background
# Terminal control returned immediately
# Logs saved to logs/uvicorn.log

# Monitor logs:
tail -f logs/uvicorn.log

# Stop services:
docker-compose down
```

### First Login
1. Navigate to the Knowledge Database at `http://your-domain.com` or `http://localhost:8000` for local development
2. Click "Login" in the top-right corner
3. Enter your credentials provided by your administrator
4. Complete two-factor authentication if enabled

### Dashboard Overview
After logging in, you'll see:
- **Search Bar**: Quick access to search functionality
- **Recent Items**: Your recently viewed knowledge items
- **Categories**: Browse by topic
- **Quick Actions**: Create, import, or manage content

## Searching for Knowledge

### Basic Search
1. Enter keywords in the search bar
2. Press Enter or click the search icon
3. Results appear ranked by relevance

### Advanced Search Options
- **Filters**: Use the filter panel to narrow results
  - By category
  - By date range
  - By author
  - By language
- **Search Operators**:
  - `"exact phrase"` - Search for exact matches
  - `title:keyword` - Search in titles only
  - `author:name` - Find content by specific author
  - `category:tech` - Limit to specific category

### AI-Powered Search
Our system uses semantic search to understand intent:
- Natural language queries supported
- Similar content suggestions
- Automatic translation for multilingual search

## Creating Knowledge Items

### Step-by-Step Creation
1. Click "Create New" button
2. Fill in required fields:
   - **Title**: Clear, descriptive title
   - **Category**: Select appropriate category
   - **Content**: Use the rich text editor
   - **Tags**: Add relevant tags for discoverability
3. Preview your content
4. Click "Save as Draft" or "Publish"

### Content Editor Features
- **Rich Text Formatting**: Bold, italic, headers, lists
- **Code Blocks**: Syntax highlighting for technical content
- **Images**: Drag and drop or paste images
- **Tables**: Create structured data
- **Links**: Internal and external linking
- **Attachments**: Upload supporting documents

### Metadata Management
- **Tags**: Add multiple tags separated by commas
- **Related Items**: Link to related knowledge
- **Language**: Specify content language
- **Access Level**: Set visibility permissions

## Managing Your Content

### My Knowledge Items
Access your created content:
1. Go to "My Content" in the user menu
2. View all your items in a list or grid
3. Use filters to find specific items
4. Bulk actions available for multiple items

### Editing and Versioning
- Click "Edit" on any of your items
- System automatically saves versions
- View version history with "History" button
- Restore previous versions if needed

### Content Status
- **Draft**: Not visible to others
- **Under Review**: Submitted for approval
- **Published**: Available to all users
- **Archived**: Hidden but preserved

## Collaboration Features

### Comments and Discussions
- Add comments to any knowledge item
- Reply to create discussion threads
- @mention users for notifications
- Mark comments as helpful

### Sharing and Export
- **Share Link**: Generate shareable links
- **Export Options**:
  - PDF for offline reading
  - Markdown for technical documentation
  - Word document for editing

### Favorites and Collections
- Star items to add to favorites
- Create custom collections
- Share collections with team members
- Subscribe to updates on specific items

## Advanced Features

### Translation Support
- Request translation for any item
- View content in multiple languages
- Contribute translations if permitted
- Automatic language detection

### Analytics Dashboard
View your contribution metrics:
- Items created
- Views generated
- Engagement rates
- Top performing content

### API Access
For technical users:
- Generate API tokens in settings
- Access content programmatically
- Integrate with other tools
- Bulk import/export capabilities

## Tips and Best Practices

### System Monitoring and Logs

When running in background mode, you can monitor the system through logs:

#### Viewing Application Logs
```bash
# Real-time log monitoring
tail -f logs/uvicorn.log

# Check for errors
grep ERROR logs/uvicorn.log

# View recent activity
tail -n 100 logs/uvicorn.log
```

#### Understanding Log Messages
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Issues requiring attention
- **DEBUG**: Detailed diagnostic information (development mode)

### Writing Good Knowledge Items
1. **Clear Titles**: Use descriptive, searchable titles
2. **Structure Content**: Use headers and sections
3. **Add Context**: Explain background and purpose
4. **Include Examples**: Practical examples help understanding
5. **Keep Updated**: Review and update regularly

### Search Tips
- Start with broad searches, then refine
- Use filters instead of complex queries
- Check suggested similar items
- Save frequent searches

### Collaboration Best Practices
- Respond to comments promptly
- Credit contributors and sources
- Review and update shared content
- Use @mentions sparingly

## Getting Help

### Support Resources
- **Help Center**: Access from the ? icon
- **Video Tutorials**: Available in Help Center
- **Contact Support**: support@your-domain.com
- **Community Forum**: Share tips with other users

### Common Issues
- **Can't find content?** Check filters and try broader search
- **Upload failed?** Check file size limits (10MB default)
- **Access denied?** Contact your administrator
- **Slow performance?** Clear browser cache

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Need Help?** Contact your system administrator or visit the Help Center