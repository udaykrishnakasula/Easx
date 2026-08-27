import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import localCoinMp4 from "@/assets/coin.mp4";

const EasyxMark = () => (
  <svg width="60%" height="60%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 5v14" />
    <path d="M20 5v14" />
    <path d="M4 12h9" />
    <path d="M13 8l4 4-4 4" />
  </svg>
);

const partners = ["Uniswap", "AAVE", "Compound", "MakerDAO"];

const RAW_VIDEO_URL =
  "https://raw.githubusercontent.com/udaykrishnakasula/Easyx-3d-coin-video-/main/gemini_generated_video_78da6d75.mp4";

export default function Hero() {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [videoSrc, setVideoSrc] = useState(RAW_VIDEO_URL);
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.defaultMuted = true;
      video.muted = true;

      // Check if already ready/cached
      if (video.readyState >= 2) {
        setIsVideoLoaded(true);
      }

      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsVideoLoaded(true);
          })
          .catch((err) => {
            console.debug("Video autoplay handled:", err);
          });
      }
    }
  }, [videoSrc]);

  const handleVideoError = () => {
    if (videoSrc !== RAW_VIDEO_URL) {
      setVideoSrc(RAW_VIDEO_URL);
    } else if (videoSrc !== "/coin.mp4") {
      setVideoSrc("/coin.mp4");
    }
  };

  const handleVideoReady = () => {
    setIsVideoLoaded(true);
  };

  // Fixed optimal position and transform styles with smooth loading fade-in
  const dynamicVideoStyle = {
    objectFit: "cover",
    objectPosition: "2% 3%",
    transform: "scale(1) translate(0px, 0px)",
    opacity: isVideoLoaded ? 1 : 0,
    transition: "opacity 0.6s ease-out",
  };

  return (
    <section className="hero font-body" data-testid="hero-section">
      {/* Brand Color Blur-Hash Placeholder Loading State */}
      <AnimatePresence>
        {!isVideoLoaded && (
          <motion.div
            className="hero__placeholder"
            data-testid="hero-video-placeholder"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Ambient blur-hash radial gradients matching brand colors */}
            <div className="hero__placeholder-mesh" />
            <div className="hero__placeholder-glow hero__placeholder-glow--1" />
            <div className="hero__placeholder-glow hero__placeholder-glow--2" />
            <div className="hero__placeholder-glow hero__placeholder-glow--3" />
            {/* Shimmer overlay */}
            <div className="hero__placeholder-shimmer" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Absolute full-coverage looping background video */}
      <video
        ref={videoRef}
        src={videoSrc}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        className="hero__video-bg responsive-hero-coin"
        style={dynamicVideoStyle}
        data-testid="hero-video"
        onLoadedData={handleVideoReady}
        onCanPlay={handleVideoReady}
        onPlaying={handleVideoReady}
        onError={handleVideoError}
      >
        <source src={RAW_VIDEO_URL} type="video/mp4" />
        <source src="/coin.mp4" type="video/mp4" />
        <source src="/assets/coin.mp4" type="video/mp4" />
        <source src={localCoinMp4} type="video/mp4" />
        Your browser does not support the video tag.
      </video>

      {/* Background fallbacks and subtle grain overlays */}
      <div className="hero__bg" style={{ backgroundImage: "url(/assets/hero_bg.jpg)" }} />
      <div className="hero__flowers" style={{ backgroundImage: "url(/assets/flowers.png)" }} />
      <div className="hero__grain" />

      {/* Navbar overlays the hero */}
      <nav className="nav" data-testid="hero-navbar">
        <a href="#" className="nav__brand" data-testid="nav-brand">
          <span className="nav__mark"><EasyxMark /></span>
          <span className="nav__name">Easyx</span>
        </a>
      </nav>

      {/* Text & CTA Container sitting cleanly in front of video (z-index: 2) */}
      <div className="hero__content">
        <div className="hero__text">
          <motion.h1
            className="hero__title font-display"
            data-testid="hero-heading"
            initial={{ opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.2, 0.8, 0.2, 1] }}
          >
            Your<br />Wealth<br />Works
          </motion.h1>
          <motion.p
            className="hero__sub"
            data-testid="hero-subtext"
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.16, ease: [0.2, 0.8, 0.2, 1] }}
          >
            An automated, reward-powered digital dollar built for native passive
            earnings and effortless connection into DeFi.
          </motion.p>
          <motion.button
            className="btn-pill hero__cta"
            data-testid="hero-join-btn"
            onClick={() => navigate("/register")}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
          >
            Join us
            <span className="hero__cta-arrow"><ArrowRight size={22} /></span>
          </motion.button>
        </div>
      </div>

      {/* Partner Logos Ticker (z-index: 2) */}
      <div className="hero__partners partners ticker" data-testid="hero-partners">
        {partners.map((p) => (
          <span key={p}>{p}</span>
        ))}
      </div>
    </section>
  );
}
