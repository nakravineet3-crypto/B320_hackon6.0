export const Colors = {
  primary: '#FF9900',
  primaryDark: '#E47911',
  nowBlue: '#1A98FF',
  deliveryYellow: '#FFD814',
  background: '#FFFFFF',
  secondaryBg: '#F3F3F3',
  trustBg: '#F0F8FF',
  border: '#DDDDDD',
  textPrimary: '#0F1111',
  textSecondary: '#565959',
  linkBlue: '#007185',
  successGreen: '#007600',
  starYellow: '#FFA41C',
  primeBadge: '#00A8E1',
  errorRed: '#CC0C39',
  sponsoredBlue: '#0066C0',
  white: '#FFFFFF',
  // Amazon Now native design tokens
  divider: '#F0F2F2', // 8px section dividers
  inputBorder: '#D5D9D9', // All input borders
  inputBorderFocus: '#FF9900',
  placeholder: '#9AA0A6',
  cardBg: '#F7F8F8', // Evidence rows, insight boxes
  nowBadge: '#007600', // Amazon Now badge
  salePrice: '#CC0C39',
  bannerGreen: '#1A6B3C',
}

export const Radius = { sm: 4, md: 4, lg: 4 } // Amazon uses 4px everywhere

export const Typography = {
  // The 3-weight system
  regular: '400' as const,
  semibold: '600' as const,
  bold: '700' as const,
  // Size scale
  xs: 10,
  sm: 11,
  base: 12,
  md: 13,
  lg: 14,
  xl: 16,
  '2xl': 18,
  '3xl': 22,
}

export const Spacing = {
  // 4px grid
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
}

export const LETTER_COLORS: Record<string, { bg: string; text: string }> = {
  plates: { bg: '#E8F5E9', text: '#2E7D32' },
  cups: { bg: '#E3F2FD', text: '#1565C0' },
  balloons: { bg: '#FFF8E1', text: '#F57F17' },
  candles: { bg: '#FCE4EC', text: '#C62828' },
  napkins: { bg: '#F3E5F5', text: '#6A1B9A' },
  decorations: { bg: '#E0F7FA', text: '#00695C' },
  return_gifts: { bg: '#FBE9E7', text: '#BF360C' },
  trash_bags: { bg: '#EFEBE9', text: '#4E342E' },
  mattress: { bg: '#E8EAF6', text: '#283593' },
  bedsheet: { bg: '#E0F2F1', text: '#00695C' },
  default: { bg: '#F5F5F5', text: '#424242' },
}

// Helper function
export function getLetterColor(category: string) {
  return LETTER_COLORS[category] || LETTER_COLORS.default
}

// Resolve a colored-letter palette from a free-form label / title
export function getLabelColor(label: string) {
  const l = (label || '').toLowerCase()
  if (l.includes('plate')) return LETTER_COLORS.plates
  if (l.includes('cup')) return LETTER_COLORS.cups
  if (l.includes('balloon')) return LETTER_COLORS.balloons
  if (l.includes('candle') || l.includes('cake')) return LETTER_COLORS.candles
  if (l.includes('napkin') || l.includes('tissue')) return LETTER_COLORS.napkins
  if (l.includes('decor') || l.includes('streamer') || l.includes('banner'))
    return LETTER_COLORS.decorations
  if (l.includes('gift') || l.includes('return')) return LETTER_COLORS.return_gifts
  if (l.includes('clean') || l.includes('trash') || l.includes('bag'))
    return LETTER_COLORS.trash_bags
  if (l.includes('mattress')) return LETTER_COLORS.mattress
  if (l.includes('bed') || l.includes('sheet')) return LETTER_COLORS.bedsheet
  return LETTER_COLORS.default
}

export const API_BASE = 'http://localhost:8000'
