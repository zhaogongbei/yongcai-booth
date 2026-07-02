import { useState, useEffect, useRef } from 'react';

interface ProgressiveImageProps {
  src: string;
  alt: string;
  microSrc?: string;
  thumbSrc?: string;
  mediumSrc?: string;
  className?: string;
  placeholderClassName?: string;
  onLoad?: () => void;
  rootMargin?: string;
  threshold?: number;
}

const ProgressiveImage = ({
  src,
  alt,
  microSrc,
  thumbSrc,
  mediumSrc,
  className = '',
  placeholderClassName = '',
  onLoad,
  rootMargin = '200px',
  threshold = 0.1,
}: ProgressiveImageProps) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string | undefined>(microSrc);
  const [loadStage, setLoadStage] = useState<'micro' | 'thumb' | 'medium' | 'full'>('micro');
  const imgRef = useRef<HTMLImageElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const hasIntersected = useRef(false);

  useEffect(() => {
    // If no micro preview is provided, start loading higher quality immediately
    if (!microSrc) {
      hasIntersected.current = true;
      loadNextStage();
      return;
    }

    // Set up Intersection Observer
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasIntersected.current) {
            hasIntersected.current = true;
            loadNextStage();
          }
        });
      },
      { rootMargin, threshold }
    );

    if (imgRef.current) {
      observerRef.current.observe(imgRef.current);
    }

    return () => {
      if (observerRef.current && imgRef.current) {
        observerRef.current.unobserve(imgRef.current);
      }
    };
  }, [microSrc, rootMargin, threshold]);

  const loadNextStage = () => {
    switch (loadStage) {
      case 'micro':
        if (thumbSrc) {
          loadImage(thumbSrc, () => {
            setLoadStage('thumb');
            setCurrentSrc(thumbSrc);
            loadNextStage();
          });
        } else if (mediumSrc) {
          loadImage(mediumSrc, () => {
            setLoadStage('medium');
            setCurrentSrc(mediumSrc);
            loadNextStage();
          });
        } else {
          loadFullImage();
        }
        break;
      case 'thumb':
        if (mediumSrc) {
          loadImage(mediumSrc, () => {
            setLoadStage('medium');
            setCurrentSrc(mediumSrc);
            loadNextStage();
          });
        } else {
          loadFullImage();
        }
        break;
      case 'medium':
        loadFullImage();
        break;
      default:
        break;
    }
  };

  const loadImage = (url: string, onSuccess: () => void) => {
    const img = new Image();
    img.src = url;
    img.onload = onSuccess;
    img.onerror = loadNextStage; // Skip to next stage if this one fails
  };

  const loadFullImage = () => {
    loadImage(src, () => {
      setCurrentSrc(src);
      setLoadStage('full');
      setIsLoaded(true);
      onLoad?.();
    });
  };

  return (
    <div ref={imgRef} className={`relative overflow-hidden ${className}`}>
      {/* Placeholder with blur effect for lower quality images */}
      {currentSrc && (
        <img
          src={currentSrc}
          alt={alt}
          className={`w-full h-full object-cover transition-opacity duration-300 ${
            loadStage === 'micro' ? 'scale-110 blur-lg' :
            loadStage === 'thumb' ? 'scale-105 blur-sm' :
            'scale-100 blur-0'
          } ${isLoaded ? 'opacity-0 absolute inset-0' : 'opacity-100'} ${placeholderClassName}`}
          aria-hidden="true"
        />
      )}

      {/* Final high quality image */}
      <img
        src={src}
        alt={alt}
        className={`w-full h-full object-cover transition-opacity duration-500 ${
          isLoaded ? 'opacity-100' : 'opacity-0 absolute inset-0'
        }`}
        loading="lazy"
      />
    </div>
  );
};

export default ProgressiveImage;
