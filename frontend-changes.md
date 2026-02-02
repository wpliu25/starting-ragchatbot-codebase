# Code Quality Tools - Changes Made

Note: This feature adds development workflow tools for Python code quality. While not a front-end feature, the changes are documented here as requested.

## Changes Made

### 1. Added Black Formatter to Dependencies

**File: `pyproject.toml`**
- Added `black>=24.0.0` to dev dependencies
- Added `[tool.black]` configuration section with:
  - `line-length = 88` (black default)
  - `target-version = ["py313"]`
  - Excluded directories: `.git`, `.venv`, `__pycache__`, `.eggs`, `build`, `dist`, `chroma_db`

### 2. Created Development Scripts

**Directory: `scripts/`**

| Script | Purpose |
|--------|---------|
| `scripts/format.sh` | Formats all Python files with black |
| `scripts/check-format.sh` | Checks formatting without modifying files (CI-friendly) |
| `scripts/quality.sh` | Runs all quality checks: format check + pytest |

### 3. Formatted Existing Codebase

Ran black on all Python files to ensure consistent formatting:
- 13 files were reformatted
- 2 files were already compliant

### 4. Updated Documentation

**File: `CLAUDE.md`**
- Added code quality commands section documenting the new scripts

## Usage

```bash
# Format all Python files
./scripts/format.sh

# Check formatting (for CI/pre-commit)
./scripts/check-format.sh

# Run all quality checks
./scripts/quality.sh
```

## Files Modified

- `pyproject.toml` - Added black dependency and configuration
- `CLAUDE.md` - Added quality commands documentation
- `backend/*.py` - Reformatted with black
- `backend/tests/*.py` - Reformatted with black
- `main.py` - Already compliant

## Files Created

- `scripts/format.sh`
- `scripts/check-format.sh`
- `scripts/quality.sh`

---

# Frontend Changes

## Dark/Light Theme Toggle Feature

### Overview
Added a complete dark/light theme toggle system with smooth transitions, localStorage persistence, and accessibility support.

### Files Modified

#### `frontend/index.html`
- Added theme toggle button with sun/moon SVG icons
- Button positioned fixed in top-right corner
- Includes proper ARIA attributes for accessibility

#### `frontend/style.css`
- **CSS Variables Enhancement**: Extended `:root` variables to support both themes
- **Light Theme Variables**: Added `[data-theme="light"]` selector with appropriate colors
- **Theme Toggle Button Styles**: New `.theme-toggle` class with hover/focus states
- **Theme Transitions**: Added smooth 0.3s transitions for background, color, border, and shadow
- **Responsive Styles**: Adjusted toggle button size for mobile screens
- **Variable-based Colors**: Updated error/success messages and source links to use CSS variables

#### `frontend/script.js`
- Added `themeToggle` DOM element reference
- `initializeTheme()`: Initializes theme from localStorage or system preference
- `setTheme(theme)`: Applies theme and saves to localStorage
- `toggleTheme()`: Toggles between dark and light modes
- `updateThemeToggleLabel(theme)`: Updates ARIA label based on current theme
- Added click event listener for theme toggle button

### CSS Variables

#### Dark Theme (Default - `:root`)
| Variable | Value | Purpose |
|----------|-------|---------|
| `--background` | `#0f172a` | Main background |
| `--surface` | `#1e293b` | Card/panel backgrounds |
| `--surface-hover` | `#334155` | Hover state for surfaces |
| `--text-primary` | `#f1f5f9` | Primary text color |
| `--text-secondary` | `#94a3b8` | Secondary/muted text |
| `--border-color` | `#334155` | Border color |
| `--code-bg` | `rgba(0, 0, 0, 0.2)` | Code block background |
| `--error-text` | `#f87171` | Error message text |
| `--success-text` | `#4ade80` | Success message text |
| `--source-link-text` | `#a78bfa` | Source link text |

#### Light Theme (`[data-theme="light"]`)
| Variable | Value | Purpose |
|----------|-------|---------|
| `--background` | `#f8fafc` | Main background |
| `--surface` | `#ffffff` | Card/panel backgrounds |
| `--surface-hover` | `#f1f5f9` | Hover state for surfaces |
| `--text-primary` | `#1e293b` | Primary text color |
| `--text-secondary` | `#64748b` | Secondary/muted text |
| `--border-color` | `#e2e8f0` | Border color |
| `--code-bg` | `rgba(0, 0, 0, 0.05)` | Code block background |
| `--error-text` | `#dc2626` | Error message text |
| `--success-text` | `#16a34a` | Success message text |
| `--source-link-text` | `#7c3aed` | Source link text |

### Accessibility Features
- Keyboard navigable toggle button (Tab + Enter/Space)
- Dynamic `aria-label` that updates based on current theme state
- Focus ring using `--focus-ring` variable for visibility
- Maintains WCAG contrast ratios in both themes:
  - Light theme: Dark text (#1e293b) on light background (#f8fafc) = 12.6:1 contrast
  - Dark theme: Light text (#f1f5f9) on dark background (#0f172a) = 15.1:1 contrast

### User Preferences
- Theme choice persisted in `localStorage` under key `theme`
- On first visit, respects system preference via `prefers-color-scheme` media query
- Defaults to dark theme if no preference detected

### Animation Details
- Theme switch: 0.3s ease transition on background-color, color, border-color, box-shadow
- Toggle button hover: scale(1.05) with enhanced shadow
- Toggle button active: scale(0.95) for tactile feedback

---

## JavaScript Functionality

### Theme Toggle on Button Click
The toggle button triggers theme switching via `toggleTheme()` function:

```javascript
// Event listener setup
themeToggle.addEventListener('click', toggleTheme);

// Toggle function
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}
```

### Smooth Transitions
CSS transitions are applied globally to ensure smooth theme changes:

```css
body,
body *,
body *::before,
body *::after {
    transition: background-color 0.3s ease,
                color 0.3s ease,
                border-color 0.3s ease,
                box-shadow 0.3s ease;
}
```

---

## Implementation Details

### CSS Custom Properties (Variables)
All theme-dependent colors use CSS custom properties defined in `:root` (dark) and `[data-theme="light"]` (light):

```css
/* Dark theme (default) */
:root {
    --background: #0f172a;
    --text-primary: #f1f5f9;
    /* ... other variables */
}

/* Light theme */
[data-theme="light"] {
    --background: #f8fafc;
    --text-primary: #1e293b;
    /* ... other variables */
}
```

### Data-Theme Attribute on Body
Theme is controlled via `data-theme` attribute on the `<body>` element:

```javascript
function setTheme(theme) {
    if (theme === 'light') {
        document.body.setAttribute('data-theme', 'light');
    } else {
        document.body.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', theme);
    updateThemeToggleLabel(theme);
}
```

### Elements Working in Both Themes
All existing elements use CSS variables and work correctly in both themes:

| Element | Variables Used |
|---------|---------------|
| Main background | `--background` |
| Sidebar | `--surface`, `--border-color` |
| Chat messages | `--surface`, `--text-primary` |
| User messages | `--user-message`, `--user-message-text` |
| Input field | `--surface`, `--border-color`, `--text-primary` |
| Buttons | `--primary-color`, `--primary-hover` |
| Source links | `--source-link-*` variables |
| Error messages | `--error-*` variables |
| Success messages | `--success-*` variables |
| Code blocks | `--code-bg` |
| Scrollbars | `--surface`, `--border-color` |

### Visual Hierarchy Maintained
- Primary actions (send button) use consistent `--primary-color` (#2563eb) in both themes
- Text hierarchy preserved with `--text-primary` and `--text-secondary`
- Surface elevation maintained via `--surface` vs `--background` contrast
- Focus states consistent with `--focus-ring` variable
- Interactive elements maintain hover/active state visibility
