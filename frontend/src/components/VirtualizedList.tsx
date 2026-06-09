import React, { useState, useRef, useEffect, useCallback } from 'react';

export interface VirtualizedListColumns {
  sm?: number;
  md?: number;
  lg?: number;
}

export interface VirtualizedListProps<T> {
  items: T[];
  renderItem: (item: T | null, index: number) => React.ReactNode;
  itemHeight: number;
  loadMore: () => void;
  hasMore: boolean;
  rowReset?: number | string;
  pageSize?: number;
  isDashboard?: boolean;
  columns?: number | VirtualizedListColumns;
}

const VirtualizedList = <T,>({
  items,
  renderItem,
  itemHeight,
  loadMore,
  hasMore,
  rowReset,
  pageSize = 6,
  isDashboard = false,
  columns = { sm: 1, md: 2, lg: 3 }
}: VirtualizedListProps<T>) => {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 0 });
  
  const getColumnCount = useCallback(() => {
    if (isDashboard) return 1; // Always 1 column in dashboard
    if (typeof columns === 'number') return columns;
    const cols = columns as VirtualizedListColumns;
    if (window.innerWidth >= 1024) return cols.lg || 3; // lg screens
    if (window.innerWidth >= 768) return cols.md || 2; // md screens
    return cols.sm || 1; // sm screens
  }, [isDashboard, columns]);

  const [columnCount, setColumnCount] = useState(getColumnCount());
  const containerRef = useRef<HTMLDivElement>(null);
  const lastLoadedRowRef = useRef<number>(-1);

  const rowGap = itemHeight === 60 ? 0 : 8;
  const rowHeight = itemHeight + rowGap;
  const totalHeight = (Math.ceil(items.length / columnCount) + (hasMore ? 1 : 0)) * rowHeight;
  const rows = Math.round(pageSize / columnCount);

  useEffect(() => {
    lastLoadedRowRef.current = -1;
  }, [rowReset]);

  const updateColumnCount = useCallback(() => {
    setColumnCount(getColumnCount());
  }, [getColumnCount]);

  const loadMoreItems = useCallback((rowIndex: number) => {
    if (rowIndex >= lastLoadedRowRef.current + rows && hasMore) {
      lastLoadedRowRef.current = rowIndex;
      loadMore();
    }
  }, [loadMore, hasMore, rows]);

  const updateVisibleRange = useCallback(() => {
    if (!containerRef.current) return;

    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const containerTop = containerRef.current.offsetTop;
    const containerHeight = window.innerHeight;

    // Calculate actual visible rows and add a small buffer (e.g. 2 rows) for smooth scrolling
    const visibleStart = Math.max(0, Math.floor((scrollTop - containerTop) / rowHeight) - 2);
    const visibleEnd = Math.min(
      Math.ceil(items.length / columnCount) + (hasMore ? 1 : 0),
      Math.ceil((scrollTop - containerTop + containerHeight) / rowHeight) + 2
    );

    setVisibleRange(prev => {
      if (prev.start === visibleStart && prev.end === visibleEnd) return prev;
      return { start: visibleStart, end: visibleEnd };
    });

    if (scrollTop + containerHeight > containerRef.current.offsetTop + containerRef.current.offsetHeight - 800 && hasMore) {
      loadMoreItems(visibleEnd);
    }
  }, [items.length, columnCount, rowHeight, hasMore, loadMoreItems]);

  useEffect(() => {
    const handleResize = () => {
      updateColumnCount();
      updateVisibleRange();
    };

    window.addEventListener('scroll', updateVisibleRange);
    window.addEventListener('resize', handleResize);
    updateVisibleRange();
    return () => {
      window.removeEventListener('scroll', updateVisibleRange);
      window.removeEventListener('resize', handleResize);
    };
  }, [updateVisibleRange, updateColumnCount]);

  const renderRow = (rowIndex: number) => {
    const startIndex = rowIndex * columnCount;
    const isShimmerRow = rowIndex === Math.ceil(items.length / columnCount) && hasMore;

    return (
      <div
        key={rowIndex}
        style={{
          height: itemHeight,
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: `${rowGap}px`
        }}
      >
        {[...Array(columnCount)].map((_, colIndex) => {
          const itemIndex = startIndex + colIndex;
          if (isShimmerRow) {
            return renderItem(null, itemIndex);
          }
          return itemIndex < items.length 
            ? renderItem(items[itemIndex], itemIndex) 
            : <div key={itemIndex} style={{ flex: 1, margin: '0 8px' }} />;
        })}
      </div>
    );
  };

  const visibleRows = [];
  for (let i = visibleRange.start; i <= visibleRange.end; i++) {
    visibleRows.push(renderRow(i));
  }

  return (
    <div ref={containerRef} className="relative w-full" style={{ minHeight: items.length > 0 ? totalHeight : 0, height: totalHeight }}>
      {items.length > 0 && visibleRange.start > 0 && <div style={{ height: visibleRange.start * rowHeight }} />}
      {visibleRows}
      {items.length > 0 && visibleRange.end < Math.ceil(items.length / columnCount) + (hasMore ? 1 : 0) && (
        <div style={{ height: (Math.ceil(items.length / columnCount) + (hasMore ? 1 : 0) - visibleRange.end - 1) * rowHeight }} />
      )}
    </div>
  );
};

export default VirtualizedList;


