import React from 'react';

function createIcon(name: string) {
  const Icon = (props: any) => React.createElement('mock-icon-' + name, props);
  Icon.displayName = name;
  return Icon;
}

export const ArrowLeft = createIcon('ArrowLeft');
export const Search = createIcon('Search');
export const Camera = createIcon('Camera');
export const History = createIcon('History');
export const User = createIcon('User');
export const ChevronRight = createIcon('ChevronRight');
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
