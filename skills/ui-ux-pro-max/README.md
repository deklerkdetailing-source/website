# UI/UX Pro Max

Design intelligence search engine for web and mobile. Covers 50+ styles, 161 color palettes, 57 font pairings, 161 product types, 99 UX guidelines, 25 chart types.

## Usage

```bash
# Generate a full design system card
python3 skills/ui-ux-pro-max/scripts/search.py "premium automotive luxury" --design-system -p "My Project"

# Search a specific domain
python3 skills/ui-ux-pro-max/scripts/search.py "glassmorphism dark" --domain style
python3 skills/ui-ux-pro-max/scripts/search.py "fintech blue" --domain colors -n 3

# Stack-specific guidelines
python3 skills/ui-ux-pro-max/scripts/search.py "navigation list" --stack react-native

# Markdown output + persist to files
python3 skills/ui-ux-pro-max/scripts/search.py "luxury spa" --design-system -f markdown --persist -p "Spa App" --page "home"
```

## Available Domains
- `product` — 161 product types
- `style` — 53 UI styles
- `colors` — 161 color palettes
- `typography` — 57 font pairings
- `landing` — 30 landing patterns
- `chart` — 25 chart types
- `ux` — 99 UX guidelines
- `google-fonts` — 82 Google Fonts
- `react` — 43 React/Next.js rules
- `web` — 44 app interface guidelines
- `prompt` — 30 AI prompt/CSS styles
- `ui-reasoning` — 52 product-to-style reasoning rules

## Stacks
- `react-native` — 44 React Native guidelines
