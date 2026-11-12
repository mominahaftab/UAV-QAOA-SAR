import { Radio, Cpu, ExternalLink, Code2 } from 'lucide-react';
import { CinematicHero } from './components/landing/CinematicHero';
import { MissionControl } from './components/dashboard/MissionControl';

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0b0c] text-[#F7F5EF] flex flex-col font-sans selection:bg-emerald-600 selection:text-white">
      {/* Fixed Sticky Header Navigation Bar */}
      <header className="fixed top-0 left-0 w-full z-50 bg-[#0a0b0c]/85 backdrop-blur-md border-b border-white/10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
          {/* Brand Logo */}
          <a href="#" className="flex items-center gap-3 group">
            <div className="p-1.5 rounded-lg bg-white/10 border border-white/15 text-[#F7F5EF] group-hover:scale-105 transition-transform">
              <Radio className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="font-exo font-extrabold text-base tracking-wider text-white flex items-center gap-2">
                <span>UAV-QAOA-SAR</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <div className="text-[10px] font-mono text-[#8f8b8a] hidden sm:block">
                RF-AWARE SEARCH-AND-RESCUE OPTIMIZATION
              </div>
            </div>
          </a>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-mono tracking-wider text-[#8f8b8a]">
            <a href="#" className="hover:text-white transition-colors">
              OVERVIEW
            </a>
            <a href="#methodology" className="hover:text-white transition-colors">
              METHODOLOGY
            </a>
            <a href="#mission-control" className="hover:text-white transition-colors">
              MISSION CONTROL
            </a>
          </nav>

          {/* Call to Action Pill */}
          <div className="flex items-center gap-3">
            <a
              href="#mission-control"
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wider transition-all shadow-sm flex items-center gap-1.5"
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>RUN OPTIMIZER</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Sections */}
      <main className="flex-1 w-full">
        {/* Section 1: Cinematic Video Scroll Landing Page */}
        <CinematicHero />

        {/* Section 2: Interactive UAV Mission Control & Radar Map */}
        <MissionControl />
      </main>

      {/* Footer */}
      <footer className="w-full bg-[#141516] border-t border-white/10 py-12 px-6 text-xs font-mono text-[#8f8b8a]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <div className="font-bold text-white text-sm">
              Quantum-Optimized UAV Waypoint Selection for Rapid Search-and-Rescue Localization
            </div>
            <div>
              University Quantum Computing Hackathon Project | Academic Research Demonstration
            </div>
            <div className="text-white/40">
              Stack: Python 3.12 • FastAPI • Qiskit Aer • SciPy MILP • React 19 • Vite • Tailwind CSS
            </div>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white flex items-center gap-2 transition-colors"
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Repository</span>
            </a>
            <a
              href="#methodology"
              className="px-3 py-1.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white flex items-center gap-1.5 transition-colors"
            >
              <span>Methodology</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
