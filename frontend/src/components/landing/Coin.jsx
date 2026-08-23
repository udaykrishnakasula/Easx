import React, { useMemo } from "react";

/**
 * Pure CSS 3D coin: engraved front/back faces, a smooth silver core (stacked
 * discs) and a reeded cylinder wall of thin radial strips so the rim shows fine
 * milled grooves that catch light like a real minted coin. GPU-only transforms.
 */
export default function Coin({ variant = "lead", discs = 18, reeds = 96, testId }) {
  const layers = useMemo(
    () =>
      Array.from({ length: discs }, (_, i) =>
        (discs === 1 ? 0 : -1 + (2 * i) / (discs - 1)).toFixed(3)
      ),
    [discs]
  );

  // each strip spans a slice of the circumference (with overlap to avoid gaps)
  const reedH = ((Math.PI / reeds) * 1.35).toFixed(4);
  const rims = useMemo(
    () =>
      Array.from({ length: reeds }, (_, i) => ({
        angle: (360 / reeds) * i,
        cls: i % 2 === 0 ? "coin__reed--a" : "coin__reed--b",
      })),
    [reeds]
  );

  const coinUrl = `url(${process.env.PUBLIC_URL}/assets/coin.png)`;

  return (
    <div className={`coin-wrap coin-wrap--${variant}`} data-testid={testId} aria-hidden="true">
      <div className="coin-perspective">
        <div className="coin-tilt">
          <div className="coin-float">
            <div className="coin">
              {layers.map((frac, i) => (
                <div
                  key={`d${i}`}
                  className="coin__disc"
                  style={{ transform: `translateZ(calc(var(--t) * ${frac}))` }}
                />
              ))}

              {rims.map((r, i) => (
                <div
                  key={`r${i}`}
                  className={`coin__reed ${r.cls}`}
                  style={{
                    height: `calc(var(--d) * ${reedH})`,
                    marginTop: `calc(var(--d) * ${(-reedH / 2).toFixed(4)})`,
                    transform: `rotateZ(${r.angle}deg) translateX(calc(var(--d) / 2)) rotateY(90deg)`,
                  }}
                />
              ))}

              <div
                className="coin__face coin__face--front"
                style={{ transform: "translateZ(var(--t))", backgroundImage: coinUrl }}
              />
              <div
                className="coin__face coin__face--back"
                style={{ transform: "translateZ(calc(var(--t) * -1)) rotateY(180deg)", backgroundImage: coinUrl }}
              />
            </div>
          </div>
        </div>
      </div>
      <div className="coin-shadow" />
    </div>
  );
}
