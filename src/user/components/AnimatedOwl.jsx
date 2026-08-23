import React from "react";

/**
 * AnimatedOwl Component
 * Recreates the cute waving purple owl animation from 1000208244.mp4
 * with a 100% transparent background, crisp vector rendering, responsive scaling,
 * continuous smooth waving, eye blinking/smiling, and gentle body bobbing.
 */
export default function AnimatedOwl({ className = "h-11 sm:h-14 w-auto" }) {
  return (
    <div className={`inline-flex items-center justify-center ${className}`} title="EasyX Owl">
      <svg
        viewBox="0 0 140 130"
        className="w-full h-full overflow-visible"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Animated Owl"
      >
        <defs>
          <style>{`
            @keyframes owl-body-bob {
              0%, 100% {
                transform: translateY(0px) rotate(0deg);
              }
              25% {
                transform: translateY(-2px) rotate(1deg);
              }
              50% {
                transform: translateY(0px) rotate(0deg);
              }
              75% {
                transform: translateY(-2.5px) rotate(-1deg);
              }
            }

            @keyframes owl-wave-wing {
              0%, 100% {
                transform: rotate(0deg);
              }
              15% {
                transform: rotate(-28deg);
              }
              30% {
                transform: rotate(10deg);
              }
              45% {
                transform: rotate(-32deg);
              }
              60% {
                transform: rotate(6deg);
              }
              75% {
                transform: rotate(-24deg);
              }
              90% {
                transform: rotate(2deg);
              }
            }

            @keyframes owl-rest-wing {
              0%, 100% {
                transform: rotate(0deg);
              }
              50% {
                transform: rotate(4deg);
              }
            }

            @keyframes owl-eyes-open {
              0%, 8%, 42%, 58%, 92%, 100% {
                opacity: 1;
                transform: scaleY(1);
              }
              12%, 38%, 62%, 88% {
                opacity: 0;
                transform: scaleY(0.1);
              }
            }

            @keyframes owl-eyes-smile {
              0%, 8%, 42%, 58%, 92%, 100% {
                opacity: 0;
              }
              12%, 38%, 62%, 88% {
                opacity: 1;
              }
            }

            .owl-container {
              transform-origin: 58px 115px;
              animation: owl-body-bob 2.4s ease-in-out infinite;
            }

            .owl-waving-wing {
              transform-origin: 82px 64px;
              animation: owl-wave-wing 2.4s ease-in-out infinite;
            }

            .owl-resting-wing {
              transform-origin: 32px 64px;
              animation: owl-rest-wing 2.4s ease-in-out infinite;
            }

            .owl-open-eye {
              transform-origin: center;
              animation: owl-eyes-open 2.4s ease-in-out infinite;
            }

            .owl-smile-eye {
              animation: owl-eyes-smile 2.4s ease-in-out infinite;
            }
          `}</style>

          {/* Gradients matching exact video hues */}
          <linearGradient id="owlBodyGrad" x1="58" y1="12" x2="58" y2="108" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#7E4CE6" />
            <stop offset="100%" stopColor="#6433C4" />
          </linearGradient>

          <linearGradient id="owlWingGrad" x1="0" y1="0" x2="35" y2="25" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
        </defs>

        <g className="owl-container">
          {/* Feet (Cyan / Bright Blue) */}
          <g id="owl-feet">
            {/* Left Foot */}
            <path
              d="M 45 106 C 45 106, 42 115, 39 116 C 36 117, 39 119, 43 118 C 45 119, 48 119, 49 117 C 51 118, 54 117, 53 115 C 51 113, 49 106, 49 106 Z"
              fill="#00C8FF"
            />
            {/* Right Foot */}
            <path
              d="M 67 106 C 67 106, 64 115, 63 116 C 61 117, 64 119, 68 118 C 70 119, 73 119, 74 117 C 76 118, 79 117, 78 115 C 76 113, 72 106, 72 106 Z"
              fill="#00C8FF"
            />
          </g>

          {/* Resting Left Wing (Viewer's left) */}
          <g className="owl-resting-wing">
            <path
              d="M 33 54 C 20 62, 16 80, 24 93 C 27 98, 33 97, 36 90 C 40 82, 38 65, 33 54 Z"
              fill="url(#owlWingGrad)"
            />
          </g>

          {/* Main Body (Purple with tufted ear horns) */}
          <path
            d="M 30 28 
               C 27 24, 21 21, 20 29 
               C 19 37, 24 45, 23 58 
               C 20 78, 25 105, 58 105 
               C 91 105, 96 78, 93 58 
               C 92 45, 97 37, 96 29 
               C 95 21, 89 24, 86 28 
               C 77 34, 69 31, 58 31 
               C 47 31, 39 34, 30 28 Z"
            fill="url(#owlBodyGrad)"
          />

          {/* Dark Violet Eye Mask / Face Patch */}
          <path
            d="M 30 38 
               C 24 45, 24 64, 38 69 
               C 47 72, 54 67, 58 60 
               C 62 67, 69 72, 78 69 
               C 92 64, 92 45, 86 38 
               C 78 44, 68 45, 58 45 
               C 48 45, 38 44, 30 38 Z"
            fill="#3B186B"
          />

          {/* Open Eyes State (Big sparkling round eyes) */}
          <g className="owl-open-eye">
            {/* Left Eye Sclera */}
            <circle cx="43" cy="53" r="12.5" fill="#FFFFFF" />
            {/* Left Eye Pupil */}
            <circle cx="44.5" cy="53" r="8" fill="#150C28" />
            {/* Left Eye Reflections */}
            <circle cx="42" cy="50" r="3.2" fill="#FFFFFF" />
            <circle cx="47.5" cy="55.5" r="1.4" fill="#FFFFFF" />

            {/* Right Eye Sclera */}
            <circle cx="73" cy="53" r="12.5" fill="#FFFFFF" />
            {/* Right Eye Pupil */}
            <circle cx="71.5" cy="53" r="8" fill="#150C28" />
            {/* Right Eye Reflections */}
            <circle cx="69" cy="50" r="3.2" fill="#FFFFFF" />
            <circle cx="74.5" cy="55.5" r="1.4" fill="#FFFFFF" />
          </g>

          {/* Smiling Eyes State (Happy curved arcs ^_^) */}
          <g className="owl-smile-eye">
            {/* Left Curved Eye */}
            <path
              d="M 33 54 Q 43 43 53 54"
              stroke="#FFFFFF"
              strokeWidth="4"
              strokeLinecap="round"
              fill="none"
            />
            {/* Right Curved Eye */}
            <path
              d="M 63 54 Q 73 43 83 54"
              stroke="#FFFFFF"
              strokeWidth="4"
              strokeLinecap="round"
              fill="none"
            />
          </g>

          {/* Cute Cyan Beak */}
          <path
            d="M 54 57 C 54 57, 58 67, 62 57 C 60 55, 56 55, 54 57 Z"
            fill="#00D2FF"
          />

          {/* Chest Feather Markings (Subtle chevrons 'v') */}
          <g stroke="#532696" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.8">
            {/* Row 1 */}
            <path d="M 47 74 L 50 78 L 53 74" />
            <path d="M 55 75 L 58 79 L 61 75" />
            <path d="M 63 74 L 66 78 L 69 74" />
            {/* Row 2 */}
            <path d="M 51 82 L 54 86 L 57 82" />
            <path d="M 59 82 L 62 86 L 65 82" />
            {/* Row 3 */}
            <path d="M 48 90 L 51 93 L 54 90" />
            <path d="M 55 90 L 58 94 L 61 90" />
            <path d="M 62 90 L 65 93 L 68 90" />
          </g>

          {/* Waving Right Wing (Viewer's right - raises, waves with 3 feather tips) */}
          <g className="owl-waving-wing">
            <path
              d="M 82 60 
                 C 94 56, 114 47, 126 55 
                 C 131 59, 131 66, 124 72 
                 C 116 79, 102 81, 91 80 
                 C 84 79, 81 72, 82 60 Z"
              fill="url(#owlWingGrad)"
            />
            {/* Wing Feather Detail */}
            <path
              d="M 112 59 C 117 63, 120 68, 123 71"
              stroke="#2563EB"
              strokeWidth="1.5"
              strokeLinecap="round"
              fill="none"
              opacity="0.6"
            />
          </g>
        </g>
      </svg>
    </div>
  );
}
