'use client';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

export function TopBarSearch() {
  return (
    <div className="bw-topbar-search">
      <Search className="bw-topbar-search-icon" />
      <input className="bw-topbar-search-input" placeholder="搜索..." type="search" />
    </div>
  );
}
