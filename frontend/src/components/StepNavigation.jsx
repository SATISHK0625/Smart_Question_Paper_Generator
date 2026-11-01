import React from 'react';
import { Upload, FileCode2, Settings, ListOrdered, FileCheck, Check } from 'lucide-react';

const STEPS = [
  { id: 1, name: 'Reference PDF', desc: 'Layout & style analysis', icon: Upload },
  { id: 2, name: 'Questions Input', desc: 'Paste text or upload file', icon: FileCode2 },
  { id: 3, name: 'Paper Config', desc: 'Exam details & metadata', icon: Settings },
  { id: 4, name: 'Structure & Edit', desc: 'Sections, marks & review', icon: ListOrdered },
  { id: 5, name: 'Compare & Review', desc: 'Visual diff, validation & export', icon: FileCheck },
];


export default function StepNavigation({ currentStep, onSelectStep, maxReachedStep }) {
  return (
    <nav aria-label="Progress" className="bg-white border-b border-slate-200 py-3 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <ol className="flex items-center justify-between sm:justify-start sm:gap-4 overflow-x-auto no-scrollbar">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = step.id < currentStep;
            const isCurrent = step.id === currentStep;
            const isAccessible = step.id <= maxReachedStep;

            return (
              <li key={step.id} className="flex-1 min-w-[130px] sm:min-w-[170px]">
                <button
                  type="button"
                  onClick={() => isAccessible && onSelectStep(step.id)}
                  disabled={!isAccessible}
                  className={`w-full group flex items-center gap-2.5 p-2 rounded-xl text-left transition-all ${
                    isCurrent
                      ? 'bg-indigo-50/80 border border-indigo-200'
                      : isAccessible
                      ? 'hover:bg-slate-50 cursor-pointer border border-transparent'
                      : 'opacity-50 cursor-not-allowed border border-transparent'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                      isCompleted
                        ? 'bg-emerald-600 text-white'
                        : isCurrent
                        ? 'bg-indigo-600 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {isCompleted ? <Check className="w-4 h-4 stroke-[3]" /> : step.id}
                  </div>
                  <div className="min-w-0">
                    <p
                      className={`text-xs font-semibold truncate ${
                        isCurrent ? 'text-indigo-900 font-bold' : isCompleted ? 'text-slate-800' : 'text-slate-500'
                      }`}
                    >
                      {step.name}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate hidden md:block">{step.desc}</p>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}
