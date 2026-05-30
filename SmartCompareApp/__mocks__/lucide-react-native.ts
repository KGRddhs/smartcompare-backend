import React from 'react';

function createIcon(name: string) {
  const Icon = (props: any) => React.createElement('mock-icon-' + name, props);
  Icon.displayName = name;
  return Icon;
}

// Lucide ships hundreds of icons. We enumerate every name we currently
// import across the app so tests don't crash with "undefined is not a
// constructor" when a screen adds a new icon. When you import a new
// lucide icon in app code, add it here too.
export const ArrowLeft = createIcon('ArrowLeft');
export const Search = createIcon('Search');
export const Camera = createIcon('Camera');
export const History = createIcon('History');
export const User = createIcon('User');
export const ChevronRight = createIcon('ChevronRight');
export const ChevronDown = createIcon('ChevronDown');
export const ChevronUp = createIcon('ChevronUp');
export const Star = createIcon('Star');
export const ThumbsUp = createIcon('ThumbsUp');
export const ThumbsDown = createIcon('ThumbsDown');
export const Trash2 = createIcon('Trash2');
export const Share2 = createIcon('Share2');
export const Check = createIcon('Check');
export const X = createIcon('X');
export const Globe = createIcon('Globe');
export const Settings = createIcon('Settings');
export const Link = createIcon('Link');
// F1.5 / F2.x / F3.x additions
export const Sparkles = createIcon('Sparkles');
export const Gift = createIcon('Gift');
export const Copy = createIcon('Copy');
export const MessageCircle = createIcon('MessageCircle');
export const Send = createIcon('Send');
export const AtSign = createIcon('AtSign');
export const Bell = createIcon('Bell');
export const Lock = createIcon('Lock');
export const Shield = createIcon('Shield');
export const MapPin = createIcon('MapPin');
export const Sliders = createIcon('Sliders');
export const FileText = createIcon('FileText');
export const ScrollText = createIcon('ScrollText');
export const LogOut = createIcon('LogOut');
export const Bookmark = createIcon('Bookmark');
export const Home = createIcon('Home');
export const Clock = createIcon('Clock');
export const Award = createIcon('Award');
export const Battery = createIcon('Battery');
export const Monitor = createIcon('Monitor');
export const Zap = createIcon('Zap');
export const HardDrive = createIcon('HardDrive');
export const DollarSign = createIcon('DollarSign');
export const Info = createIcon('Info');
export const AlertCircle = createIcon('AlertCircle');
export const ExternalLink = createIcon('ExternalLink');
export const Trophy = createIcon('Trophy');
export const HelpCircle = createIcon('HelpCircle');
export const Image = createIcon('Image');
// Bundle E S1.2 — LoginScreen + S1.3 SaveAdvisor additions.
export const ChevronLeft = createIcon('ChevronLeft');
export const Mail = createIcon('Mail');
// Bundle B/C/D Task 2.9 — CategorySelector lucide swap (per-icon imports).
export const Smartphone = createIcon('Smartphone');
export const ShoppingCart = createIcon('ShoppingCart');
export const Pill = createIcon('Pill');
export const Brush = createIcon('Brush');
export const Scissors = createIcon('Scissors');
export const Flower = createIcon('Flower');
export const ShoppingBag = createIcon('ShoppingBag');
export const Package = createIcon('Package');
// Bundle E S2.W2 — Step08Priorities per-priority glyphs.
export const ShieldCheck = createIcon('ShieldCheck');
export const Hammer = createIcon('Hammer');
export const MousePointerClick = createIcon('MousePointerClick');
export const Leaf = createIcon('Leaf');
export const HeartPulse = createIcon('HeartPulse');
// Bundle E F-S2.W2.hotfix (task #38) — Step10 + Step11 per-option glyphs.
// Camera + Search + ShoppingBag + ShieldCheck + Zap + Sparkles already
// declared above; add Users + Music + MoreHorizontal.
export const Users = createIcon('Users');
export const Music = createIcon('Music');
export const MoreHorizontal = createIcon('MoreHorizontal');
// Bundle E F-S2.X3 — EditPreferencesFlow LifestylePicker per-tag glyphs.
// HeartPulse + Leaf already declared above; add 9 new tag icons.
// All verified as lucide-react-native@1.14.0 exports.
export const Coins = createIcon('Coins');
export const Cpu = createIcon('Cpu');
export const Gem = createIcon('Gem');
export const Minus = createIcon('Minus');
export const Heart = createIcon('Heart');
export const Plane = createIcon('Plane');
export const ChefHat = createIcon('ChefHat');
export const Mountain = createIcon('Mountain');
export const Palette = createIcon('Palette');
