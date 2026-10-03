# content-source Specification

## Purpose
Keeps page content (text, metadata, structured items) separate from presentation and reads it through one access layer, so the content source can move from in-repo static data to Markdown, MDX or a CMS without rewriting pages.
## Requirements
### Requirement: Content defined as typed data
Page content SHALL be stored as typed, serializable data (strings, numbers, booleans, arrays, plain objects) outside page and component files. Content data MUST NOT contain rendered markup or framework elements.

#### Scenario: Editing content does not touch presentation
- **WHEN** the home page title is changed in its content entry
- **THEN** the rebuilt home page shows the new title and no page or component file was edited

#### Scenario: Content is serializable
- **WHEN** any content entry is converted to JSON and back
- **THEN** the result is equal to the original entry

### Requirement: Single content access layer
Pages SHALL read content only through a content access layer that exposes asynchronous lookups (for example by page slug). Pages and components MUST NOT import raw content data files directly.

#### Scenario: Swapping the source
- **WHEN** the access layer's implementation is changed to read from a different source that returns the same content types
- **THEN** no page or component file needs to change

### Requirement: Page metadata comes from content
Each page's title and description SHALL come from its content entry through the access layer, so SEO metadata moves together with the content.

#### Scenario: Metadata follows content
- **WHEN** a page's content entry defines a title and description
- **THEN** the rendered page's `<title>` and meta description match those values

### Requirement: Missing content fails the build
A lookup for content that does not exist SHALL cause a build error that names the missing entry, instead of producing an empty page.

#### Scenario: Unknown slug
- **WHEN** a page requests content for a slug that has no entry
- **THEN** the build fails and the error message includes that slug

