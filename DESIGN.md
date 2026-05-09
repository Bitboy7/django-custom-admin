# Design System — Agrícola de la Costa

## Overview

Sistema visual para el ERP administrativo de Agrícola de la Costa San Luis. El diseño equilibra densidad de datos financieros con una estética profesional agrícola premium. Basado en Tailwind CSS v2 (CDN) con tokens CSS custom en el admin.

## Theme

**Light default**, dark mode disponible en admin (Jazzmin toggle). La interfaz está optimizada para uso prolongado en oficina y uso ocasional en campo con tablets bajo luz solar.

## Color

### Strategy: Committed
Una paleta terrostra y orgánica inspirada en la costa de Sinaloa: el carbón azulado de la tierra húmeda, la pizarra de los días nublados, y el menta pálido del mar en calma. Sin verdes artificiales, sin azules corporativos genéricos. La identidad agrícola se transmite por textura y tono, no por clichés de color.

### Palette (oficial)

| Token | Hex | Uso |
|-------|-----|-----|
| `--color-black` | `#000000` | Texto principal puro |
| `--color-charcoal-blue` | `#2f4550` | Navbar, fondos oscuros, botones primarios, headers de tabla |
| `--color-blue-slate` | `#586f7c` | Hover en navbar, iconos secundarios, bordes sutiles |
| `--color-light-blue` | `#b8dbd9` | Acento cálido, badges de éxito, highlights, focus rings |
| `--color-ghost-white` | `#f4f4f9` | Fondo de página, cards, superficies |
| `--color-danger` | `#b85450` | Errores, alertas (rojo terracota, no rojo brillante) |
| `--color-warning` | `#c9a227` | Advertencias (ocre dorado) |
| `--color-surface` | `#ffffff` | Superficie elevada sobre ghost-white |
| `--color-text-primary` | `#000000` | Texto principal |
| `--color-text-secondary` | `#2f4550` | Texto secundario (charcoal-blue) |
| `--color-text-muted` | `#586f7c` | Labels, placeholders (blue-slate) |
| `--color-border` | `#d8dce6` | Bordes suaves sobre ghost-white |
| `--color-border-focus` | `#b8dbd9` | Borde en focus (light-blue) |

### OKLCH References (para futuras iteraciones)
- Charcoal-blue: oklch(35% 0.04 245)
- Blue-slate: oklch(52% 0.05 245)
- Light-blue: oklch(82% 0.06 195)
- Ghost-white: oklch(97% 0.005 270)

## Typography

| Rol | Fuente | Fallback | Uso |
|-----|--------|----------|-----|
| Display | Playfair Display | Georgia, serif | Títulos de página, headers de sección (admin) |
| Body | Plus Jakarta Sans | system-ui, sans-serif | Todo el texto de UI, tablas, formularios |
| Mono | JetBrains Mono | Consolas, monospace | Números, IDs, fechas técnicas, tablas financieras |

### Scale
- Page title: 1.5rem (24px), weight 700
- Section title: 1.125rem (18px), weight 600
- Card title: 0.875rem (14px), weight 700
- Body: 0.8125rem (13px), weight 400
- Caption/label: 0.75rem (12px), weight 500
- KPI value: 1.15rem, weight 800

### Line length
- Máximo 75ch en textos largos (reportes, descripciones).
- Tablas: nowrap en celdas de datos cortos; max-width con truncate en descripciones.

## Spacing

Base: 0.25rem (4px). Escalado Tailwind estándar.

- Page padding: 1.25rem (20px)
- Card padding: 1rem (16px) body, 0.625rem 1rem header
- Card gap: 1rem (16px) entre cards
- Input padding: 0.375rem 0.625rem
- Section gap: 1.25rem (20px)

## Components

### Cards
- `background: white`, `border-radius: 0.5rem`
- Sombra sutil: `0 1px 3px rgba(0,0,0,.07), 0 0 0 1px rgba(0,0,0,.04)`
- **Sin side-stripe borders**. Los KPI cards usan `border-left: 3px solid` como única excepción intencional para codificación de color rápida.
- Hover en KPI: `translateY(-2px)` + sombra aumentada.

### Inputs & Selects
- `border: 1px solid #d1d5db`, `border-radius: 0.375rem`
- Focus: `border-color: #3b82f6`, `box-shadow: 0 0 0 3px rgba(59,130,246,.15)`
- Selects custom: `appearance-none` con flecha SVG absoluta a la derecha.
- Estados de error: borde rojo, fondo rojo-50, texto rojo-600.

### Buttons
- Primario: `bg-charcoal-blue (#2f4550)`, hover `bg-blue-slate (#586f7c)`, texto blanco.
- Éxito/Guardar: `bg-charcoal-blue`, hover `bg-blue-slate`, con acento `light-blue` en iconos.
- Peligro: `bg-danger (#b85450)`, hover oscurecer 10%.
- Ghost: borde `blue-slate`, fondo `ghost-white`, hover `light-blue` tint.
- Todos: `border-radius: 0.375rem`, `transition-colors duration-200`.

### Badges
- Categoría: `bg-ghost-white text-charcoal-blue border-blue-slate`, rounded-sm, font-semibold.
- Éxito: `bg-light-blue/20 text-charcoal-blue`.
- Peligro: `bg-danger/10 text-danger`.
- Warning: `bg-warning/10 text-warning`.

### Tables
- Header: `bg-charcoal-blue`, texto blanco, uppercase, letter-spacing.
- Filas odd: `bg-ghost-white`.
- Hover: `bg-light-blue/15`.
- Font size: 0.8rem en celdas.
- Scrollbar thin: 5px, track `ghost-white`, thumb `blue-slate/30`.

### Toast Notifications
- Posición: fixed top-right.
- Border-left: 4px solid (color según tipo).
- Sombra: `shadow-xl`.
- Entrada: `translate-x-full -> translate-x-0`, `opacity-0 -> 1`.

## Motion

- **Easing principal**: `cubic-bezier(0.25, 1, 0.5, 1)` (ease-out-quart).
- **Duración estándar**: 200ms para hover, focus, cambios de estado.
- **Duración de entrada**: 300ms para toasts, modales, dropdowns.
- **Skeleton screens**: shimmer con `linear-gradient` animado, duración 1.5s, ease-in-out.
- **No animar**: width, height, top, left. Usar transform y opacity.
- **Respetar `prefers-reduced-motion`**: desactivar shimmer y transiciones no esenciales.

## Layout

### Admin (Jazzmin)
- Sidebar navy (`#1e3a8a`), contenido con padding 1.25rem.
- Navbar sticky top, z-30.
- Dashboard: grid de KPIs (6 cols en xl), 2 cols para gráficos, 1 col para tabla.

### Vistas públicas/corporativas
- Navbar azul-900, contenido con max-w-4xl/7xl centrado.
- Formularios: max-w-2xl centrado para flujos simples, max-w-7xl para tablas complejas.

## Elevation

- Card base: `0 1px 3px rgba(0,0,0,.07), 0 0 0 1px rgba(0,0,0,.04)`
- Card hover (KPI): `0 6px 18px rgba(0,0,0,.11)`
- Dropdown: `0 10px 15px -3px rgba(0,0,0,.1)`
- Toast/modal: `0 25px 50px -12px rgba(0,0,0,.25)`

## HTMX Patterns

- **Swap strategy**: `innerHTML` para reemplazo total de secciones; `beforeend` para append (listas).
- **Loading states**: `hx-indicator` con spinner inline; skeleton screens para reemplazos grandes.
- **Toast feedback**: respuestas HTMX con header `HX-Trigger` para eventos de toast (éxito/error).
- **Confirmación**: `hx-confirm` nativo para acciones destructivas; evitar modales innecesarios.
- **No full reloads**: los filtros de tabla deben actualizar solo tbody + KPIs, no toda la página.
