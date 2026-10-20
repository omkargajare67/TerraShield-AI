import React, { useRef, useEffect, useCallback } from 'react';

interface BrandIntroProps {
  onComplete: () => void;
  videoSrc?: string;
}

/**
 * BrandIntro
 * Full-screen startup brand intro covering the complete browser viewport
 * with a pure white background (#FFFFFF). The underlying application is not
 * rendered while the intro plays. When the video ends, onComplete is called
 * to reveal the TerraShield AI application.
 */
export const BrandIntro: React.FC<BrandIntroProps> = ({
  onComplete,
  videoSrc = '/animations/terrashield-intro.mp4',
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const finishedRef = useRef(false);

  const handleFinish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onComplete();
  }, [onComplete]);

  // Lock body scroll while splash is active
  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  // Ensure autoplay triggers reliably
  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.play().catch((err) => {
        console.warn('Intro video autoplay prevented, waiting for user interaction or finishing:', err);
      });
    }

    // Safety fallback timeout to prevent users from ever being permanently trapped
    const safetyTimeout = setTimeout(() => {
      handleFinish();
    }, 7500);

    return () => clearTimeout(safetyTimeout);
  }, [handleFinish]);

  return (
    <div
      id="terrashield-startup-intro"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100%',
        height: '100vh',
        minHeight: '100dvh',
        backgroundColor: '#ffffff',
        zIndex: 2147483647,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      <video
        ref={videoRef}
        src={videoSrc}
        autoPlay
        muted
        playsInline
        controls={false}
        onEnded={handleFinish}
        onError={handleFinish}
        style={{
          width: '100%',
          height: '100%',
          maxWidth: '100vw',
          maxHeight: '100dvh',
          objectFit: 'contain',
          objectPosition: 'center',
          backgroundColor: '#ffffff',
          display: 'block',
        }}
      />
    </div>
  );
};
