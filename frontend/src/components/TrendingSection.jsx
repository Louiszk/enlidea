import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import NodeCard from './NodeCard'
import PaperCard from './PaperCard';

const ChevronLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-white">
    <path fillRule="evenodd" d="M7.72 12.53a.75.75 0 010-1.06l7.5-7.5a.75.75 0 111.06 1.06L9.31 12l6.97 6.97a.75.75 0 11-1.06 1.06l-7.5-7.5z" clipRule="evenodd" />
  </svg>
);

const ChevronRightIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 text-white">
    <path fillRule="evenodd" d="M16.28 11.47a.75.75 0 010 1.06l-7.5 7.5a.75.75 0 01-1.06-1.06L14.69 12 7.72 5.03a.75.75 0 011.06-1.06l7.5 7.5z" clipRule="evenodd" />
  </svg>
);

const TrendingSection = ({ title, data, highImpact, isPapers = false }) => {
    const [showArrows, setShowArrows] = useState(false);
    const [showLeftArrow, setShowLeftArrow] = useState(false);
    const [showRightArrow, setShowRightArrow] = useState(true);
    const [isScrollable, setIsScrollable] = useState(false);
    const scrollContainerRef = useRef(null);
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
      const checkIfTouch = () => {
        // Check if the device has touch capabilities
        const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        setIsMobile(hasTouch); //&& window.innerWidth <= 1024);
      };
  
      checkIfTouch();
      window.addEventListener('resize', checkIfTouch);
  
      return () => window.removeEventListener('resize', checkIfTouch);
    }, []);
  
    const handleScroll = () => {
        const container = scrollContainerRef.current;
        if (container) {
          setShowLeftArrow(container.scrollLeft > 0);
          setShowRightArrow(container.scrollLeft < container.scrollWidth - container.clientWidth - 1);
          setIsScrollable(container.scrollWidth > container.clientWidth);
        }
      };
    
      useEffect(() => {
        const container = scrollContainerRef.current;
        if (container) {
          container.addEventListener('scroll', handleScroll);
          handleScroll();
          
          // Check scrollability on window resize
          const checkScrollability = () => {
            setIsScrollable(container.scrollWidth > container.clientWidth);
          };
          window.addEventListener('resize', checkScrollability);
          
          return () => {
            container.removeEventListener('scroll', handleScroll);
            window.removeEventListener('resize', checkScrollability);
          };
        }
      }, []);
  
    const scroll = (direction) => {
      const container = scrollContainerRef.current;
      if (container) {
        const smallScreen = window.innerWidth <= 640;
        const scrollAmount = direction === 'left' ? (smallScreen ? -272 : -336) : (smallScreen ? 272 : 336);
        container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
      }
    };

    const items = data.nodes || data.results || data.papers || [];
  
    return (
      <>
          <div className='flex justify-between items-end text-gray-200 mb-4'>
            <h2 className="text-base sm:text-xl md:text-2xl font-bold">{title}</h2>
            {isScrollable && !isPapers &&
            <Link to={highImpact ? `/explore?sort=${highImpact}&page=1`
               :
              data.category ? `/categories/${data.category.slug}` : (data.type && data.tag ? `/explore?sort=trending&filters={"tags"%3A"${data.tag}"%2C"types"%3A"${data.type}"}&page=1` : "#")}
             className="hover:underline font-semibold text-sm sm:text-base">View all</Link>}
        </div>
        <div className="relative"
          onMouseEnter={() => setShowArrows(true)} 
          onMouseLeave={() => setShowArrows(false)}
        >
          {(showArrows || isMobile) && (showLeftArrow ?
            <button
              className="absolute left-0 top-1/2 transform -translate-y-1/2 bg-gray-800 bg-opacity-70 p-2 rounded-md h-full z-10 transition-opacity duration-300"
              onClick={() => scroll('left')}
            >
              <ChevronLeftIcon />
            </button> :
            <div className="absolute left-0 top-1/2 transform -translate-y-1/2 p-2 rounded-md h-full w-8 z-10"/>
          )}
          {(showArrows || isMobile) && (showRightArrow ? 
            <button
              className="absolute right-0 top-1/2 transform -translate-y-1/2 bg-gray-800 bg-opacity-70 p-2 rounded-md h-full z-10 transition-opacity duration-300"
              onClick={() => scroll('right')}
            >
              <ChevronRightIcon />
            </button> :
            <div className="absolute right-0 top-1/2 transform -translate-y-1/2 p-2 rounded-md h-full w-8 z-10"/>
          )}
          <div
            ref={scrollContainerRef}
            className="flex overflow-x-auto space-x-4 scrollbar-hide"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {items.map((item) => (
              <div key={`${item.id}_${title}`} className="min-w-64 max-w-64 sm:min-w-80 sm:max-w-80 flex-shrink-0">
                {isPapers ? <PaperCard paper={item} /> : <NodeCard node={item} />}
              </div>
            ))}
          </div>
        </div>
      </>
    );
  };
export default TrendingSection;
