import React from "react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Coin from "./Coin";

const EasyxMark = () => (
  <svg width="60%" height="60%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 5v14" />
    <path d="M20 5v14" />
    <path d="M4 12h9" />
    <path d="M13 8l4 4-4 4" />
  </svg>
);

const partners = ["Aave", "Compound", "MakerDAO", "Chainlink", "Curve"];

export default function Hero() {
  const navigate = useNavigate();
  return (
    <section className="hero font-body" data-testid="hero-section">
      <div className="hero__bg" style={{ backgroundImage: `url(${process.env.PUBLIC_URL}/assets/hero_bg.jpg)` }} />

      {/* Navbar overlays the hero */}
      <nav className="nav" data-testid="hero-navbar">
        <a href="#" className="nav__brand" data-testid="nav-brand">
          <span className="nav__mark"><EasyxMark /></span>
          <span className="nav__name">Easyx</span>
        </a>
      </nav>

      {/* 3D coins — dominant foreground, same composition on every size */}
      <Coin variant="lead" reeds={104} testId="hero-coin-lead" />
      <Coin variant="sub" discs={14} reeds={68} testId="hero-coin-sub" />
      <Coin variant="mini" discs={12} reeds={52} testId="hero-coin-mini" />

      <div className="hero__flowers" style={{ backgroundImage: `url(${process.env.PUBLIC_URL}/assets/flowers.png)` }} />
      <div className="hero__grain" />

      {/* Text block, left-anchored */}
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

      <div className="hero__partners" data-testid="hero-partners">
        {partners.map((p) => (
          <span key={p}>{p}</span>
        ))}
      </div>
    </section>
  );
}
