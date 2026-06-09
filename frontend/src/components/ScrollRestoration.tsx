import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const scrollPositions: Record<string, number> = {};
const MAX_ATTEMPTS = 10;

function ScrollRestoration() {
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      scrollPositions[location.pathname] = window.scrollY;
    };

    const savedPosition = scrollPositions[location.pathname];

    window.history.scrollRestoration = 'manual';

    const waitForElement = (attempt = 0) => {
      if (
        document.body.scrollHeight >= savedPosition + window.innerHeight ||
        attempt >= MAX_ATTEMPTS ||
        !savedPosition
      ) {
        window.scrollTo({
          top: savedPosition,
          //behavior: 'smooth',
        });
      } else {
        setTimeout(() => waitForElement(attempt + 1), 100);
      }
    };

    if (savedPosition !== undefined) {
      waitForElement();
    }

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.history.scrollRestoration = 'auto';
    };
  }, [location]);

  return null;
}

export default ScrollRestoration;

