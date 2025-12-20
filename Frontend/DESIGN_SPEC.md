# AuraAI Design Specification

## Design Philosophy

AuraAI follows a **minimal, high-contrast** design philosophy inspired by OpenAI. The interface prioritizes clarity, readability, and ease of use with a strict black & white color palette.

### Core Principles
1. **Clarity First** - Every element serves a purpose
2. **Minimal Decoration** - No unnecessary visual noise
3. **Strong Typography** - Hierarchy through size and weight
4. **Consistent Spacing** - Based on 4px grid system
5. **Accessibility** - WCAG AA standards met throughout

## Color System

### Primary Colors
| Token | Value | Usage |
|-------|-------|-------|
| Pure Black | #000000 | Text, primary buttons, borders |
| Pure White | #ffffff | Background, text on dark |

### Neutral Grays
| Token | Value | Usage |
|-------|-------|-------|
| Dark Gray | #0f0f0f | Dark backgrounds |
| Darker Gray | #1a1a1a | Section backgrounds |
| Darkest Gray | #2b2b2b | Hover states, depth |
| Medium Gray | #767676 | Secondary text, disabled |
| Light Gray | #d1d1d1 | Borders, dividers |
| Border | #e5e5e5 | Light borders |

### Semantic Colors
| Token | Value | Usage |
|-------|-------|-------|
| Shadow Light | rgba(0,0,0,0.1) | Subtle shadows |
| Shadow Dark | rgba(0,0,0,0.3) | Medium shadows |
| Error | #ef4444 | Error states |
| Error Light | #fej2f2 | Error backgrounds |

## Typography

### Font Stack
\`\`\`css
Primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif
Mono: 'Menlo', 'Monaco', monospace
\`\`\`

### Heading Styles

#### H1 (Hero)
- Size: 3.5rem (56px) / Mobile: 2.25rem
- Weight: 700
- Line Height: 1.2
- Letter Spacing: -0.02em
- Use: Page titles, hero sections

#### H2 (Section)
- Size: 2.25rem (36px)
- Weight: 700
- Line Height: 1.3
- Letter Spacing: -0.01em
- Use: Section headings

#### H3 (Subsection)
- Size: 1.5rem (24px)
- Weight: 600
- Line Height: 1.4
- Use: Component titles, card headers

#### H4 (Component)
- Size: 1.125rem (18px)
- Weight: 600
- Line Height: 1.4
- Use: Sub-headings, labels

### Body Text
- Size: 1rem (16px)
- Weight: 400
- Line Height: 1.6
- Color: Gray Medium (#767676)
- Use: Body copy, descriptions

### Small Text
- Size: 0.9rem, 0.85rem
- Weight: 400
- Color: Gray Medium
- Use: Meta information, captions

## Spacing System

Based on 4px base unit:

\`\`\`
1:   4px    (--space-1)
2:   8px    (--space-2)
3:  12px    (--space-3)
4:  16px    (--space-4)
5:  20px    (--space-5)
6:  24px    (--space-6)
8:  32px    (--space-8)
10: 40px    (--space-10)
12: 48px    (--space-12)
\`\`\`

### Application
- **Padding**: Internal component spacing
- **Margin**: Between components
- **Gap**: Between flex items
- **Never mix** margin/padding with gap on same element

## Components

### Buttons

#### Primary Button
\`\`\`
Background: #000000
Text: #ffffff
Padding: 12px 32px
Border: None
Hover: scale(1.02), shadow
State: Active, disabled
\`\`\`

#### Secondary Button
\`\`\`
Background: Transparent
Text: #000000
Border: 1px solid #000000
Hover: Background #000000, Text #ffffff
\`\`\`

#### Ghost Button
\`\`\`
Background: Transparent
Text: #767676
Border: None
Hover: Text #000000
\`\`\`

### Cards

**Base Style**
\`\`\`
Background: #ffffff
Border: 1px solid #e5e5e5
Padding: 24px
Border Radius: 12px
Box Shadow: none (add on hover)
\`\`\`

**Interactive**
- Hover: Border to #000000, shadow 0 8px 24px rgba(0,0,0,0.1)
- Active: Transform scale or background shift

### Input Fields

**State: Default**
\`\`\`
Background: #ffffff
Border: 1px solid #e5e5e5
Padding: 12px 16px
Border Radius: 8px
Font Size: 1rem
\`\`\`

**State: Focus**
\`\`\`
Border: 1px solid #000000
Box Shadow: 0 0 0 2px rgba(0,0,0,0.05)
\`\`\`

**State: Disabled**
\`\`\`
Background: #1a1a1a
Opacity: 0.6
Cursor: not-allowed
\`\`\`

**State: Error**
\`\`\`
Border: 1px solid #ef4444
Background: #fef2f2
\`\`\`

### Navigation

#### Main Navbar
- Height: 64px
- Background: #ffffff with backdrop blur
- Border Bottom: 1px solid #e5e5e5
- Sticky positioning on scroll
- Logo + Menu items + Auth buttons

#### Dashboard Sidebar
- Width: 280px
- Background: #ffffff
- Border Right: 1px solid #e5e5e5
- Active state: Background #1a1a1a, left border
- User profile at bottom

### Hero Section

**Layout**: Two-column grid
- Left: Text content
- Right: Visual (SVG, image)

**Typography**:
- Headline: 3.5rem, weight 700
- Subheading: 1.125rem, color gray-medium
- CTA buttons: Primary + Secondary

### Feature Grid

**Layout**: 3-column (auto-fit, minmax 300px)
**Cards**: Border, hover effect, icon + text

### Tables & Lists

**Task Cards**:
- Checkbox + content + metadata
- Hover: Border highlight, shadow
- Done state: Opacity 0.6, strikethrough title

**Meeting Cards**:
- Header with title + date
- Summary paragraph
- Footer with metadata
- Clickable, hover effect

## Responsive Design

### Breakpoints
- **Mobile**: < 480px
- **Tablet**: 480px - 768px
- **Desktop**: 768px+

### Mobile-First Rules
1. Single column by default
2. Stack navigation vertically
3. Hamburger menu < 768px
4. Full-width forms
5. Larger touch targets (48px min)

### Key Adjustments
- Navbar: 56px on mobile, 64px desktop
- Font sizes: Reduced on mobile (clamp())
- Grid: 1 column on mobile, auto-fit on larger
- Padding: Reduced on mobile

## Motion & Animations

### Principles
- Subtle, purposeful motion
- Respect `prefers-reduced-motion`
- 200-300ms transition durations
- Easing: ease, ease-in-out

### Common Transitions
\`\`\`css
/* Hover effects */
transition: all 0.2s ease;

/* Loading states */
animation: pulse 2s infinite;

/* Page transitions */
transition: opacity 0.3s ease;
\`\`\`

### Disabled Motion
\`\`\`css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
\`\`\`

## Dark Mode Consideration

Currently not supported (black & white only). If adding:
1. Create dark theme CSS variables
2. Add system preference detection
3. Add manual toggle in settings
4. Test WCAG AA contrast in both modes

## Accessibility

### Color Contrast
- Text on background: 4.5:1 minimum (WCAG AA)
- Large text (18pt+): 3:1 minimum
- Used 100% verified ratios throughout

### Keyboard Navigation
- All interactive elements keyboard accessible
- Logical tab order
- Focus indicators visible (2px outline)
- Skip to main content link

### Screen Readers
- Semantic HTML (nav, main, section)
- ARIA labels on icon buttons
- Form labels properly associated
- No redundant alt text

### Motor Control
- Touch targets: 48px minimum
- Hover + focus states
- No time-based interactions
- Ample click areas

## Design Tokens Summary

\`\`\`javascript
// Stored in globals.css as CSS variables
--color-bg: #ffffff
--color-fg: #000000
--color-bg-dark: #0f0f0f
--color-gray-medium: #767676
--space-1: 4px
--space-4: 16px
--radius-md: 8px
\`\`\`

## Future Enhancements

- [ ] Dark mode support
- [ ] Animated SVG illustrations
- [ ] Smooth page transitions
- [ ] Advanced data visualizations
- [ ] Custom icons set
- [ ] Micro-interactions
- [ ] Advanced loading states

---

For implementation questions, reference the component files in `src/components/`.
