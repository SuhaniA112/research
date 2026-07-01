import { BookOpen, GraduationCap, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { SelectionCard } from "@/components/ui/StatCard";
import { Tag } from "@/components/ui/Tag";
import { InputField } from "@/components/ui/InputField";
import { allResearchAreas, currentUser } from "@/data/mockData";
import type { ReadingLevel } from "@/types";

export function OnboardingPage() {
  const navigate = useNavigate();
  const [areas, setAreas] = useState<string[]>(currentUser.researchAreas);
  const [keywords, setKeywords] = useState<string[]>(currentUser.keywords);
  const [keywordInput, setKeywordInput] = useState("");
  const [readingLevel, setReadingLevel] = useState<ReadingLevel>("graduate");
  const [occupation, setOccupation] = useState("");
  const [institution, setInstitution] = useState("");
  const [emailOptIn, setEmailOptIn] = useState(true);
  const [email, setEmail] = useState("");

  function toggleArea(area: string) {
    setAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area],
    );
  }

  function addKeyword() {
    const kw = keywordInput.trim();
    if (kw && !keywords.includes(kw)) {
      setKeywords((prev) => [...prev, kw]);
      setKeywordInput("");
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Welcome {currentUser.name}!</h1>
      <p className="mt-2 text-sm text-gray-600">
        Answer a couple questions about yourself to help us find the relevant sources for your
        research!
      </p>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-900">
          What topics are you interested in? <span className="text-red-500">*</span>
        </h2>
        <p className="mt-4 text-xs font-semibold text-gray-700">Research Area(s)</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {allResearchAreas.map((area) => (
            <button key={area} type="button" onClick={() => toggleArea(area)}>
              <Tag variant={areas.includes(area) ? "brand" : "outline"}>{area}</Tag>
            </button>
          ))}
          <Tag variant="outline">Add Topic +</Tag>
        </div>

        <p className="mt-4 text-xs font-semibold text-gray-700">Specific Keywords</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-gray-300 px-3 py-2">
          {keywords.map((kw) => (
            <Tag key={kw} variant="brand" onRemove={() => setKeywords((p) => p.filter((k) => k !== kw))}>
              {kw}
            </Tag>
          ))}
          <input
            type="text"
            placeholder="Add keywords..."
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
            className="min-w-[120px] flex-1 border-0 bg-transparent text-sm outline-none"
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-900">
          Reading level? <span className="text-red-500">*</span>
        </h2>
        <p className="mt-1 text-xs text-gray-500">
          We&apos;ll adjust our sources to match your level. Can be changed at anytime.
        </p>
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
          placeholder="i.e. Student"
          value={occupation}
          onChange={(e) => setOccupation(e.target.value)}
        />
        <InputField
          label="Current institution?"
          placeholder="i.e. Cornell University"
          value={institution}
          onChange={(e) => setInstitution(e.target.value)}
        />
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-900">
          Receive fresh, relevant content straight to your inbox!
        </h2>
        <div className="mt-3 flex gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={emailOptIn}
              onChange={() => setEmailOptIn(true)}
              className="accent-brand-700"
            />
            Email Me!
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!emailOptIn}
              onChange={() => setEmailOptIn(false)}
              className="accent-brand-700"
            />
            Not interested
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-700 focus:outline-none"
          />
          <button
            type="button"
            className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800"
          >
            Submit
          </button>
        </div>
      </section>

      <div className="mt-10 flex justify-end">
        <button
          type="button"
          onClick={() => navigate("/hub")}
          className="text-sm font-medium text-brand-700 hover:underline"
        >
          Continue →
        </button>
      </div>
    </div>
  );
}
