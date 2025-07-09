# How to Add a New Section to the Expose Template System

This guide explains how to add a new section to the expose template system. The expose template system allows property managers and tenant admins to customize the content shown in property exposes.

## Overview

The expose template system consists of several components:
1. **Backend Models & Schemas** - Define the data structure
2. **Database Migration** - Update the database schema
3. **Frontend Types** - TypeScript interfaces
4. **Template Editor** - UI for editing content
5. **Expose View** - Display the content
6. **Translations** - Multi-language support

## Step-by-Step Guide

### 1. Define the Section in Backend Schema

First, decide what type of content your section will have:
- **Simple text**: Use a `str` field
- **List of items**: Create a new type and use `List[YourType]`
- **Complex structured data**: Create multiple types as needed

#### A. For Simple Text Section

In `/app/schemas/business.py`, add to `ExposeTemplateBase`:

```python
class ExposeTemplateBase(BaseSchema):
    # ... existing fields ...
    your_section_content: Optional[str] = Field(None, description="Content for your section")
```

#### B. For List-Based Section

First, create the item type in `/app/schemas/expose_template_types.py`:

```python
class YourSectionItem(BaseModel):
    """Item for your section"""
    title: str = Field(..., description="Item title")
    description: Optional[str] = Field(None, description="Optional description")
    # Add more fields as needed
```

Then add to `/app/schemas/business.py`:

```python
# Import your type
from app.schemas.expose_template_types import (
    # ... existing imports ...
    YourSectionItem
)

class ExposeTemplateBase(BaseSchema):
    # ... existing fields ...
    your_section_items: Optional[List[YourSectionItem]] = Field(None, description="Your section items")
```

### 2. Update the Database Model

In `/app/models/business.py`, add the corresponding field:

```python
class ExposeTemplate(Base, TenantMixin, AuditMixin):
    # ... existing fields ...
    
    # For simple text:
    your_section_content = Column(Text, nullable=True)
    
    # For JSON data:
    your_section_items = Column(JSON, nullable=True)
```

### 3. Add to Section Visibility Controls

In `/app/schemas/expose_template_types.py`, add your section to `EnabledSections`:

```python
class EnabledSections(BaseModel):
    """Section visibility configuration"""
    # ... existing fields ...
    your_section: bool = Field(default=True)  # Set default visibility
```

### 4. Create Database Migration

Run the Alembic migration:

```bash
source venv/bin/activate
alembic revision --autogenerate -m "Add your_section to expose templates"
```

Review and run the migration:

```bash
alembic upgrade head
```

### 5. Update Default Content

In `/app/utils/default_template_content.py`, add default content:

```python
# For simple text
DEFAULT_YOUR_SECTION_CONTENT = "Your default content here"

# For list items
DEFAULT_YOUR_SECTION_ITEMS = [
    {"title": "Item 1", "description": "Description 1"},
    {"title": "Item 2", "description": "Description 2"},
]

def get_default_template_content():
    return {
        # ... existing fields ...
        "your_section_content": DEFAULT_YOUR_SECTION_CONTENT,
        # or
        "your_section_items": DEFAULT_YOUR_SECTION_ITEMS
    }
```

### 6. Update Frontend Types

Generate new TypeScript types:

```bash
cd digitales-expose-frontend
npm run generate-types
```

### 7. Add to Template Editor

In `/digitales-expose-frontend/app/[locale]/dashboard/expose-templates/edit/page.tsx`:

#### A. Add the tab trigger:

```tsx
<TabsList>
  {/* ... existing tabs ... */}
  <TabsTrigger value="your_section">{t('exposeTemplate.yourSection')}</TabsTrigger>
</TabsList>
```

#### B. Add the tab content:

For simple text:
```tsx
<TabsContent value="your_section">
  <Card>
    <CardHeader>
      <CardTitle>{t('exposeTemplate.yourSection')}</CardTitle>
      <CardDescription>{t('exposeTemplate.yourSectionDescription')}</CardDescription>
    </CardHeader>
    <CardContent>
      <Textarea
        value={template.your_section_content || ''}
        onChange={(e) => setTemplate({
          ...template,
          your_section_content: e.target.value
        })}
        rows={5}
        placeholder={t('exposeTemplate.yourSectionPlaceholder')}
      />
    </CardContent>
  </Card>
</TabsContent>
```

For list items:
```tsx
<TabsContent value="your_section">
  <Card>
    <CardHeader>
      <CardTitle>{t('exposeTemplate.yourSection')}</CardTitle>
      <CardDescription>{t('exposeTemplate.yourSectionDescription')}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {template.your_section_items?.map((item, index) => (
        <div key={index} className="p-4 border rounded-lg space-y-3">
          {/* Add input fields for each item property */}
          <Input
            value={item.title}
            onChange={(e) => updateYourSectionItem(index, 'title', e.target.value)}
            placeholder={t('exposeTemplate.itemTitle')}
          />
          {/* Add remove button */}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => removeYourSectionItem(index)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button onClick={addYourSectionItem} variant="outline">
        <Plus className="mr-2 h-4 w-4" />
        {t('exposeTemplate.addYourSectionItem')}
      </Button>
    </CardContent>
  </Card>
</TabsContent>
```

#### C. Add helper functions for list management:

```tsx
const updateYourSectionItem = (index: number, field: string, value: string) => {
  if (!template) return
  const items = [...(template.your_section_items || [])]
  items[index] = {
    ...items[index],
    [field]: value
  }
  setTemplate({
    ...template,
    your_section_items: items
  })
}

const addYourSectionItem = () => {
  if (!template) return
  setTemplate({
    ...template,
    your_section_items: [
      ...(template.your_section_items || []),
      { title: "", description: null }
    ]
  })
}

const removeYourSectionItem = (index: number) => {
  if (!template) return
  const items = [...(template.your_section_items || [])]
  items.splice(index, 1)
  setTemplate({
    ...template,
    your_section_items: items
  })
}
```

### 8. Add to Expose View

In `/digitales-expose-frontend/components/expose/expose-view.tsx`:

#### A. Add to navigation menu:

```tsx
const sections = useMemo(() => [
  // ... existing sections ...
  ...(isSectionVisible('your_section') ? [{ 
    id: 'your-section', 
    label: t('exposeTemplate.sections.your_section'), 
    icon: YourIcon 
  }] : []),
], [cityInfo, imagesByType.interior, isSectionVisible])
```

#### B. Add the section rendering:

```tsx
{/* Your Section - INVENIO Style */}
{isSectionVisible('your_section') && (
  <section 
    id="your-section" 
    ref={el => { if (el) sectionRefs.current['your-section'] = el }} 
    className="py-16 md:py-20 lg:py-24 px-6 md:px-12 lg:px-16 bg-white"
  >
    <div className="max-w-7xl mx-auto">
      <div className="text-center mb-12 lg:mb-16">
        <h2 className="text-3xl md:text-4xl lg:text-5xl font-light text-gray-600 mb-2">
          {t('exposeTemplate.yourSectionTitle')}
        </h2>
        <h3 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-4">
          {t('exposeTemplate.yourSectionSubtitle')}
        </h3>
        <div className="w-24 md:w-32 h-1 bg-amber-400 mx-auto"></div>
      </div>
      
      {/* For simple text */}
      {template?.your_section_content && (
        <div className="prose prose-lg mx-auto">
          <p>{template.your_section_content}</p>
        </div>
      )}
      
      {/* For list items */}
      {template?.your_section_items && template.your_section_items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {template.your_section_items.map((item, index) => (
            <Card key={index}>
              <CardHeader>
                <CardTitle>{item.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  </section>
)}
```

### 9. Add Translations

In both `/digitales-expose-frontend/messages/en.json` and `/de.json`:

```json
{
  "exposeTemplate": {
    "sections": {
      "your_section": "Your Section Name"
    },
    "yourSection": "Your Section",
    "yourSectionTitle": "Your Section",
    "yourSectionSubtitle": "SUBTITLE",
    "yourSectionDescription": "Description of what this section contains",
    "yourSectionPlaceholder": "Enter content for this section...",
    "addYourSectionItem": "Add Item",
    "itemTitle": "Title",
    "itemDescription": "Description"
  }
}
```

### 10. Update Template Overview

In `/digitales-expose-frontend/app/[locale]/dashboard/expose-templates/page.tsx`, add your section to the overview:

```tsx
const sections = [
  // ... existing sections ...
  { 
    name: t('exposeTemplate.sections.your_section'), 
    key: "your_section",
    icon: "🎯", // Choose appropriate emoji
    enabled: template?.enabled_sections?.your_section !== false,
    hasContent: !!template?.your_section_content, // or check items length
    contentCount: template?.your_section_items?.length || 0,
    description: t('exposeTemplate.yourSectionDescription')
  }
]
```

## Best Practices

1. **Naming Convention**: Use snake_case for backend fields and camelCase for frontend
2. **Default Values**: Always provide sensible defaults
3. **Validation**: Add proper validation in schemas
4. **Translations**: Add all user-facing text to translation files
5. **Styling**: Follow the existing INVENIO style pattern
6. **Testing**: Test the entire flow from editing to display

## Common Section Types

### 1. Text Section
- Simple paragraph or multi-paragraph text
- Use `Text` column in database
- Use `Textarea` in editor

### 2. List Section
- Multiple items with consistent structure
- Use `JSON` column in database
- Provide add/remove functionality in editor

### 3. Key-Value Section
- Settings or configuration options
- Can use JSON or separate columns
- Use appropriate input controls

### 4. Rich Content Section
- May include HTML or markdown
- Consider using a rich text editor
- Ensure proper sanitization

## Troubleshooting

1. **Migration fails**: Check for syntax errors in model definitions
2. **Types not generated**: Ensure backend is running when generating types
3. **Section not visible**: Check `enabled_sections` configuration
4. **Content not saving**: Verify field names match between frontend and backend
5. **Translation missing**: Add keys to both language files

## Example: Adding a "Testimonials" Section

Here's a complete example of adding a testimonials section:

1. **Schema** (`expose_template_types.py`):
```python
class TestimonialItem(BaseModel):
    author: str = Field(..., description="Testimonial author name")
    role: Optional[str] = Field(None, description="Author's role or title")
    content: str = Field(..., description="Testimonial content")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5")
```

2. **Model** (`business.py`):
```python
testimonials = Column(JSON, nullable=True)
```

3. **Enabled Sections**:
```python
testimonials: bool = Field(default=True)
```

4. **Default Content**:
```python
DEFAULT_TESTIMONIALS = [
    {
        "author": "Max Mustermann",
        "role": "Investor",
        "content": "Excellent investment opportunity with great returns.",
        "rating": 5
    }
]
```

This creates a complete testimonials section that can be managed through the template editor and displayed in the expose view.