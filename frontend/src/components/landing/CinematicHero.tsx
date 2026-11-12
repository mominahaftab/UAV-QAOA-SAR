import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ArrowDown, Cpu, ShieldCheck, Compass, Zap, Target } from 'lucide-react';

interface FeatureBlock {
  number: string;
  tag: string;
  title: string;
  description: string;
  mathHighlight?: string;
  icon: ReactNode;
  align: 'left' | 'right';
}

const FEATURE_BLOCKS: FeatureBlock[] = [
  {
    number: '01',
    tag: 'OPERATIONAL RESILIENCE',
    title: 'Mission-Critical Multi-Coverage',
    description:
      'In high-stakes Search-and-Rescue, single-drone observation risks occlusions and false negatives. Our mathematical formulation enforces at least k-fold sensing coverage (k ≥ 3) for every target location from a minimal set of UAV waypoints.',
    mathHighlight: '\\sum_{i \\in W} A_{ji} x_i \\ge k, \\quad \\forall j \\in T',
    icon: <Target className="w-5 h-5 text-cyan-400" />,
    align: 'left',
  },
  {
    number: '02',
    tag: 'MATHEMATICAL EMBEDDING',
    title: 'Exact QUBO & Ising Mapping',
    description:
      'Transforms the NP-hard constrained k-coverage problem into an unconstrained quadratic binary Hamiltonian using slack variables. Penalty multiplier λ is bounded (tested default λ = 7.0) to strictly guarantee ground-state feasibility.',
    mathHighlight: 'H_C = \\sum_{i=1}^N x_i + \\lambda \\sum_{j=1}^M \\left( \\sum_{i=1}^N A_{ji} x_i - k - b_{j0} - 2 b_{j1} \\right)^2',
    icon: <Cpu className="w-5 h-5 text-indigo-400" />,
    align: 'right',
  },
  {
    number: '03',
    tag: 'QUANTUM ALGORITHM',
    title: 'QAOA Circuit Optimization',
    description:
      'Implements the Quantum Approximate Optimization Algorithm using p-layer parameterized cost and mixer unitaries. Optimized via fast statevector expectation routines and evaluated via finite-shot Aer simulation.',
    mathHighlight: '|\\gamma, \\beta\\rangle = \\prod_{l=1}^p e^{-i \\beta_l H_M} e^{-i \\gamma_l H_C} |+\\rangle^{\\otimes n}',
    icon: <Zap className="w-5 h-5 text-amber-400" />,
    align: 'left',
  },
  {
    number: '04',
    tag: 'CLASSICAL VERIFICATION',
    title: 'Rigorous Multi-Solver Benchmarks',
    description:
      'The classical solver explores 2^6 = 64 waypoint subsets, while the full QUBO operates across 16 binary variables (6 waypoint + 10 slack), yielding 2^16 = 65,536 bitstrings simulated with Qiskit Aer.',
    mathHighlight: '\\text{Classical: } 2^6 = 64 \\text{ subsets} \\quad \\vert \\quad \\text{QUBO / QAOA: } 2^{16} = 65,536 \\text{ states}',
    icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
    align: 'right',
  },
  {
    number: '05',
    tag: 'SYSTEM ARCHITECTURE',
    title: 'Real-Time Mission Control',
    description:
      'FastAPI REST backend with SQLite/PostgreSQL persistence, coupled to an interactive 2D coordinate radar map rendering target radar signatures, selected UAV waypoints, and active sensing beams in real time.',
    mathHighlight: 'REST \\to \\text{FastAPI} \\to \\text{Qiskit Aer} \\to \\text{React Mission Control}',
    icon: <Compass className="w-5 h-5 text-rose-400" />,
    align: 'left',
  },
];

export const CinematicHero: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const blocksContainerRef = useRef<HTMLDivElement>(null);
  const lastBlockRef = useRef<HTMLDivElement>(null);

  // Smooth scrubbing state
  const targetTimeRef = useRef<number>(0);
  const currentTimeRef = useRef<number>(0);
  const rafIdRef = useRef<number | null>(null);

  const [isVideoLoaded, setIsVideoLoaded] = useState<boolean>(false);
  const [scrollProgress, setScrollProgress] = useState<number>(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Ensure video NEVER autoplays or loops
    video.pause();
    video.currentTime = 0;

    const handleLoadedMetadata = () => {
      setIsVideoLoaded(true);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    if (video.readyState >= 1) {
      setIsVideoLoaded(true);
    }

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
    };
  }, []);

  // Scroll listener applying the exact freight-train scroll math
  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current || !lastBlockRef.current || !videoRef.current) return;

      const video = videoRef.current;
      const vh = window.innerHeight;
      const containerRect = containerRef.current.getBoundingClientRect();
      const containerTop = -containerRect.top; // pixels scrolled past top of container

      // Position of the last block relative to container top
      const lastBlockRect = lastBlockRef.current.getBoundingClientRect();
      const lastBlockBottom = lastBlockRect.bottom - containerRect.top;

      // Mathematical mapping
      const end = lastBlockBottom + 0.75 * vh;
      const knee = Math.max(0.01, Math.min(0.99, lastBlockBottom / end));
      const p = Math.max(0, Math.min(1, containerTop / end));

      // Two-part piecewise clip progress
      let clipProgress = 0;
      if (p < knee) {
        clipProgress = (p / knee) * 0.46;
      } else {
        clipProgress = 0.46 + ((p - knee) / (1 - knee)) * 0.54;
      }
      clipProgress = Math.max(0, Math.min(1, clipProgress));

      setScrollProgress(clipProgress);

      const duration = video.duration || 10;
      const effectiveDuration = Math.max(0.1, duration - 1 / 48);
      targetTimeRef.current = clipProgress * effectiveDuration;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll);
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
    };
  }, [isVideoLoaded]);

  // RAF smoothing loop for video.currentTime
  useEffect(() => {
    let active = true;

    const tick = () => {
      if (!active) return;
      const video = videoRef.current;
      if (video && video.readyState >= 1) {
        const diff = targetTimeRef.current - currentTimeRef.current;
        if (Math.abs(diff) > 0.003) {
          currentTimeRef.current += diff * 0.22;
          try {
            video.currentTime = currentTimeRef.current;
          } catch {
            // ignore seek errors during quick scrolls
          }
        }
      }
      rafIdRef.current = requestAnimationFrame(tick);
    };

    rafIdRef.current = requestAnimationFrame(tick);

    return () => {
      active = false;
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full bg-[#0a0b0c] text-[#F7F5EF]">
      {/* Sticky Background Video Track */}
      <div className="sticky top-0 left-0 w-full h-screen overflow-hidden z-0 pointer-events-none">
        <video
          ref={videoRef}
          className="w-full h-full object-cover brightness-[0.45] contrast-[1.15]"
          playsInline
          muted
          preload="auto"
          poster="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/5e018553-cb8a-420a-819f-fcdfa08e5df0.jpg"
        >
          <source
            src="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/e02bb27f-80d8-445f-a03e-1b609dac4261.mp4"
            type="video/mp4"
            media="(min-width: 768px)"
          />
          <source
            src="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/e8eb434f-d097-4b1b-b9e6-c8b46fa43040.mp4"
            type="video/mp4"
          />
        </video>

        {/* Ambient Dark Gradients & Grid Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b0c] via-transparent to-[#0a0b0c]/80" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0a0b0c]/80 via-transparent to-[#0a0b0c]/80" />
        <div className="absolute inset-0 opacity-[0.07] bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:24px_24px]" />

        {/* HUD Mission Telemetry Overlay */}
        <div className="absolute top-6 left-8 hidden md:flex items-center gap-3 text-xs font-mono tracking-widest text-[#F7F5EF]/80 bg-black/50 backdrop-blur-md px-3.5 py-1.5 rounded border border-white/10">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>SIMULATION RADAR: LOCAL CARTESIAN (METRES)</span>
          <span className="text-white/30">|</span>
          <span>SCRUB SYNC: {(scrollProgress * 100).toFixed(1)}%</span>
        </div>
      </div>

      {/* Hero Header Content (Scroll Layer 1) */}
      <div className="relative z-10 min-h-screen flex flex-col justify-center items-center px-6 text-center pt-24 pb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono tracking-wider text-cyan-300 bg-cyan-950/60 border border-cyan-500/30 mb-8 backdrop-blur-md shadow-lg shadow-cyan-950/40">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          QUANTUM COMPUTING HACKATHON BENCHMARK
        </div>

        {/* 4-Line Exo 2 Headline */}
        <h1 className="font-exo font-extrabold text-5xl sm:text-7xl md:text-8xl lg:text-9xl tracking-tight text-[#F7F5EF] leading-[0.92] drop-shadow-[0_4px_24px_rgba(0,0,0,0.85)] max-w-6xl">
          SEARCH SMARTER.<br />
          COVER FASTER.<br />
          RESPOND BETTER.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 via-rose-400 to-amber-300">
            SAVE LIVES.
          </span>
        </h1>

        <p className="mt-8 max-w-2xl text-lg sm:text-xl text-[#F7F5EF]/80 font-sans font-light leading-relaxed drop-shadow-md">
          Quantum-Optimized UAV Waypoint Selection for Rapid Search-and-Rescue Localization.
          Solving $k$-coverage combinatorial optimization via exact QUBO mapping and parameterized QAOA circuits.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center gap-4">
          <a
            href="#mission-control"
            className="px-8 py-3.5 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-exo font-bold text-base tracking-wide transition-all shadow-lg shadow-cyan-500/25 flex items-center gap-2 group"
          >
            <span>LAUNCH MISSION CONTROL</span>
            <ArrowDown className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
          </a>
          <a
            href="#methodology"
            className="px-6 py-3.5 rounded bg-white/10 hover:bg-white/15 text-[#F7F5EF] font-exo font-semibold text-base tracking-wide transition-all border border-white/20 backdrop-blur-md"
          >
            TECHNICAL ARCHITECTURE
          </a>
        </div>

        <div className="mt-16 animate-bounce text-white/40 flex flex-col items-center gap-2 text-xs font-mono">
          <span>SCROLL TO SCRUB TIMELINE</span>
          <ArrowDown className="w-4 h-4" />
        </div>
      </div>

      {/* 5 Mirrored Feature Blocks (Scroll Layer 2) */}
      <div ref={blocksContainerRef} className="relative z-10 max-w-7xl mx-auto px-6 py-24 space-y-48">
        {FEATURE_BLOCKS.map((block, index) => {
          const isLeft = block.align === 'left';
          const isLast = index === FEATURE_BLOCKS.length - 1;

          return (
            <div
              key={block.number}
              ref={isLast ? lastBlockRef : undefined}
              className={`flex flex-col md:flex-row items-center ${
                isLeft ? 'md:justify-start' : 'md:justify-end'
              }`}
            >
              <div
                className={`w-full md:w-7/12 lg:w-1/2 p-8 sm:p-10 rounded-2xl bg-gradient-to-b from-[#0c121e]/90 to-[#070b12]/95 border border-cyan-500/20 backdrop-blur-xl shadow-2xl shadow-black/80 hover:border-cyan-400/40 transition-colors ${
                  isLeft ? 'md:mr-auto' : 'md:ml-auto'
                }`}
              >
                <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                      {block.icon}
                    </div>
                    <span className="text-xs font-mono font-bold tracking-widest text-cyan-400">
                      {block.tag}
                    </span>
                  </div>
                  <span className="text-2xl font-exo font-black text-white/30">
                    {block.number}
                  </span>
                </div>

                <h3 className="font-exo font-bold text-2xl sm:text-3xl text-[#F7F5EF] mb-3">
                  {block.title}
                </h3>

                <p className="text-white/70 font-sans text-sm sm:text-base leading-relaxed mb-5">
                  {block.description}
                </p>

                {block.mathHighlight && (
                  <div className="p-3.5 rounded-lg bg-black/60 border border-white/10 font-mono text-xs text-cyan-200/90 overflow-x-auto shadow-inner">
                    <code>{block.mathHighlight}</code>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Cloud Section Transition (-34vh pull-up effect) */}
      <div
        id="methodology"
        className="relative z-20 -mt-[25vh] pt-32 pb-24 bg-gradient-to-b from-[#0a0b0c] via-[#e2dedd] to-[#0a0b0c] text-slate-900 transition-colors"
      >
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="px-3 py-1 rounded-full text-xs font-mono font-bold tracking-wider text-slate-800 bg-black/10 border border-black/15">
              HACKATHON VERIFICATION & TECHNICAL HONESTY
            </span>
            <h2 className="mt-4 font-exo font-extrabold text-3xl sm:text-5xl text-slate-950 tracking-tight">
              Rigorous Engineering. Zero Fake Quantum Hype.
            </h2>
            <p className="mt-4 max-w-2xl mx-auto text-slate-700 font-sans text-base">
              Search-and-rescue localization lives or dies on verified guarantees. We contrast exact quantum formulation against classical baselines with total mathematical transparency.
            </p>
          </div>

          {/* 4 Credibility Editorial Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="p-8 rounded-xl bg-white/80 backdrop-blur-md border border-slate-300 shadow-xl">
              <div className="text-cyan-700 font-mono text-xs font-bold tracking-wider mb-2">01 / MATHEMATICAL BOUNDS</div>
              <h4 className="font-exo font-bold text-xl text-slate-950 mb-2">
                Analytical Penalty Multiplier Guarantee
              </h4>
              <p className="text-slate-700 text-sm leading-relaxed">
                We avoid ad-hoc penalty tuning by enforcing λ &gt; λ_min = 6.0. This guarantees that violating any k-fold coverage constraint incurs an energy penalty strictly higher than the cost of selecting all available waypoints, making infeasible states provably sub-optimal.
              </p>
            </div>

            <div className="p-8 rounded-xl bg-white/80 backdrop-blur-md border border-slate-300 shadow-xl">
              <div className="text-indigo-700 font-mono text-xs font-bold tracking-wider mb-2">02 / REALISTIC NISQ EVALUATION</div>
              <h4 className="font-exo font-bold text-xl text-slate-950 mb-2">
                Transparent 29% Feasible Sampling Yield
              </h4>
              <p className="text-slate-700 text-sm leading-relaxed">
                Rather than fabricating a false quantum speedup on 16 qubits, we report real Aer simulation metrics: at p=1, QAOA achieves a 29% feasible sampling rate and finds the exact optimum (4 waypoints, 0.00 optimality gap) within 500 shots.
              </p>
            </div>

            <div className="p-8 rounded-xl bg-white/80 backdrop-blur-md border border-slate-300 shadow-xl">
              <div className="text-emerald-700 font-mono text-xs font-bold tracking-wider mb-2">03 / CLASSICAL DUAL-VERIFICATION</div>
              <h4 className="font-exo font-bold text-xl text-slate-950 mb-2">
                SciPy MILP &amp; Exact Enumeration
              </h4>
              <p className="text-slate-700 text-sm leading-relaxed">
                Every optimization experiment is cross-checked against exact Branch-and-Cut MILP (HiGHS solver) and exhaustive 2^N state exploration, providing an unshakeable ground-truth baseline for quantum fidelity analysis.
              </p>
            </div>

            <div className="p-8 rounded-xl bg-white/80 backdrop-blur-md border border-slate-300 shadow-xl">
              <div className="text-rose-700 font-mono text-xs font-bold tracking-wider mb-2">04 / FULL-STACK INTEGRATION</div>
              <h4 className="font-exo font-bold text-xl text-slate-950 mb-2">
                FastAPI, Qiskit &amp; Interactive UI
              </h4>
              <p className="text-slate-700 text-sm leading-relaxed">
                A modern asynchronous Python 3.12 architecture paired with SQLAlchemy ORM and Alembic migrations, exposing clean REST endpoints to drive real-time UAV mission planning and interactive radar visualization.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
