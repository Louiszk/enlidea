import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import VirtualizedList from './VirtualizedList';

// Mock window.innerWidth
const setWidth = (width) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
};

describe('VirtualizedList', () => {
  const mockItems = Array.from({ length: 10 }, (_, i) => ({ id: i, name: `Item ${i}` }));
  const mockRenderItem = (item, index) => (
    <div key={item ? item.id : `empty-${index}`} data-testid="list-item" style={{ flex: 1 }}>
      {item ? item.name : 'Empty Slot'}
    </div>
  );

  beforeEach(() => {
    setWidth(1024);
    vi.clearAllMocks();
  });

  it('renders correctly with multiple items in a row', () => {
    render(
      <VirtualizedList
        items={mockItems}
        renderItem={mockRenderItem}
        itemHeight={100}
        loadMore={() => {}}
        hasMore={false}
      />
    );
    
    // On desktop (1024px), columnCount should be 3
    const items = screen.getAllByTestId('list-item');
    expect(items.length).toBeGreaterThan(0);
  });

  it('maintains grid structure with empty slots when items are few', () => {
    // 1 item, but 3 columns on desktop
    const singleItem = [mockItems[0]];
    render(
      <VirtualizedList
        items={singleItem}
        renderItem={mockRenderItem}
        itemHeight={100}
        loadMore={() => {}}
        hasMore={false}
        columns={{ sm: 1, md: 2, lg: 3 }}
      />
    );

    // Should render the actual item
    expect(screen.getByText('Item 0')).toBeInTheDocument();
    const listItem = screen.getByTestId('list-item');
    const row = listItem.parentElement;
    
    expect(row.children.length).toBe(3);
    // The first child is our item, the next two are the placeholder divs
    expect(row.children[0]).toHaveTextContent('Item 0');
    expect(row.children[1]).toBeEmptyDOMElement();
    expect(row.children[2]).toBeEmptyDOMElement();
  });

  it('adjusts column count based on window width', () => {
    // Mock mobile width
    setWidth(480);
    
    const { rerender } = render(
      <VirtualizedList
        items={mockItems}
        renderItem={mockRenderItem}
        itemHeight={100}
        loadMore={() => {}}
        hasMore={false}
        columns={{ sm: 1, md: 2, lg: 3 }}
      />
    );

    let listItem = screen.getAllByTestId('list-item')[0];
    let row = listItem.parentElement;
    expect(row.children.length).toBe(1);

    // Mock tablet width
    setWidth(800);
    window.dispatchEvent(new Event('resize'));
    
    rerender(
        <VirtualizedList
          items={mockItems}
          renderItem={mockRenderItem}
          itemHeight={100}
          loadMore={() => {}}
          hasMore={false}
          columns={{ sm: 1, md: 2, lg: 3 }}
        />
      );

    listItem = screen.getAllByTestId('list-item')[0];
    row = listItem.parentElement;
    expect(row.children.length).toBe(2);
  });
});
