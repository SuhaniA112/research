import {
  BookOpen,
  ChevronRight,
  GraduationCap,
  LogOut,
  Lock,
  Save,
  Search,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { SelectionCard, StatCard } from "@/components/ui/StatCard";
import { Tag } from "@/components/ui/Tag";
import { Toggle } from "@/components/ui/Toggle";
import { InputField } from "@/components/ui/InputField";
import { allResearchAreas, currentUser } from "@/data/mockData";
import type { ReadingLevel } from "@/types";

export function ProfilePage() {
  const [areas, setAreas] = useState<string[]>(currentUser.researchAreas);
  const [keywords, setKeywords] = useState<string[]>(currentUser.keywords);
  const [keywordInput, setKeywordInput] = useState("");
  const [readingLevel, setReadingLevel] = useState<ReadingLevel>(currentUser.readingLevel);
  const [occupation, setOccupation] = useState(currentUser.occupation);
  const [institution, setInstitution] = useState(currentUser.institution);
  const [weeklyDigest, setWeeklyDigest] = useState(currentUser.weeklyDigest);
  const [sourceNotifications, setSourceNotifications] = useState(currentUser.sourceNotifications);

  function toggleArea(area: string) {
    setAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area],
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Profile & Settings</h1>
        <div className="flex gap-2">
          <button
            type="button"
            className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
          >
            <Save className="h-4 w-4" />
            Save changes
          </button>
        </div>
      </div>

      <div className="mt-8 flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-700 text-2xl font-bold text-white">
          {currentUser.name[0]}
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">{currentUser.fullName}</h2>
          <p className="text-sm text-gray-500">
            {currentUser.occupation} · Member since {currentUser.memberSince}
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <StatCard
          label="SOURCES SAVED"
          value={`${currentUser.sourcesSaved}`}
          subtext={`across ${currentUser.projectsCount} projects`}
        />
        <StatCard
          label="PROJECTS"
          value={`${currentUser.projectsCount}`}
          subtext={`${currentUser.activeProjectsThisMonth} active this month`}
        />
        <StatCard
          label="NOTES WRITTEN"
          value={`${currentUser.notesWritten}`}
          subtext={`last note ${currentUser.lastNoteDaysAgo} days ago`}
        />
      </div>

      <section className="mt-8">
        <p className="text-sm font-medium text-gray-900">Research Area(s)</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {allResearchAreas.map((area) => (
            <button key={area} type="button" onClick={() => toggleArea(area)}>
              <Tag variant={areas.includes(area) ? "brand" : "outline"}>{area}</Tag>
            </button>
          ))}
          <Tag variant="outline">Add Topic +</Tag>
        </div>

        <p className="mt-4 text-sm font-medium text-gray-900">Specific Keywords</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-gray-300 px-3 py-2">
          {keywords.map((kw) => (
            <Tag
              key={kw}
              variant="brand"
              onRemove={() => setKeywords((p) => p.filter((k) => k !== kw))}
            >
              {kw}
            </Tag>
          ))}
          <input
            type="text"
            placeholder="Add keywords..."
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                const kw = keywordInput.trim();
                if (kw && !keywords.includes(kw)) {
                  setKeywords((p) => [...p, kw]);
                  setKeywordInput("");
                }
              }
            }}
            className="min-w-[120px] flex-1 border-0 bg-transparent text-sm outline-none"
          />
        </div>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-medium text-gray-900">Reading level?</h3>
        <p className="text-xs text-gray-500">We&apos;ll adjust our sources to match your level.</p>
        <div className="mt-4 flex gap-3">
          <SelectionCard
            icon={<BookOpen className="h-5 w-5" />}
            title="Casual Reader"
            description="Plain language summaries."
            selected={readingLevel === "casual"}
            onClick={() => setReadingLevel("casual")}
          />
          <SelectionCard
            icon={<GraduationCap className="h-5 w-5" />}
            title="Graduate Level"
            description="More technical."
            selected={readingLevel === "graduate"}
            onClick={() => setReadingLevel("graduate")}
          />
          <SelectionCard
            icon={<Search className="h-5 w-5" />}
            title="Expert"
            description="More specific and analytical."
            selected={readingLevel === "expert"}
            onClick={() => setReadingLevel("expert")}
          />
        </div>
      </section>

      <section className="mt-8 space-y-4">
        <InputField
          label="Current occupation?"
          required
          value={occupation}
          onChange={(e) => setOccupation(e.target.value)}
          placeholder="i.e. Student"
        />
        <InputField
          label="Current institution?"
          value={institution}
          onChange={(e) => setInstitution(e.target.value)}
          placeholder="i.e. Cornell University"
        />
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold text-gray-900">Preferences</h3>
        <div className="mt-3 divide-y divide-gray-200 rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm text-gray-700">Weekly digest emails</span>
            <Toggle checked={weeklyDigest} onChange={setWeeklyDigest} />
          </div>
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm text-gray-700">New source notifications</span>
            <Toggle checked={sourceNotifications} onChange={setSourceNotifications} />
          </div>
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm text-gray-700">Email address</span>
            <span className="text-sm text-gray-500">{currentUser.email}</span>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <h3 className="text-sm font-semibold text-gray-900">Account</h3>
        <div className="mt-3 divide-y divide-gray-200 rounded-xl border border-gray-200">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm text-gray-700 hover:bg-gray-50"
          >
            <span className="flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Change password
            </span>
            <ChevronRight className="h-4 w-4 text-gray-400" />
          </button>
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm text-red-600 hover:bg-red-50"
          >
            <span className="flex items-center gap-2">
              <Trash2 className="h-4 w-4" />
              Delete account
            </span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
