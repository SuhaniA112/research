import { BookOpen, GraduationCap, Microscope } from "lucide-react";
import { type KeyboardEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useCreateProject } from "@/api/projects";
import { getResearchAreaOptions } from "@/api/profile";
import { SelectionCard } from "@/components/ui/StatCard";
import { ResearchAreaPicker } from "@/components/ui/ResearchAreaPicker";
import { Tag } from "@/components/ui/Tag";
import { InputField } from "@/components/ui/InputField";
import type { ReadingLevel } from "@/types";

export function NewProjectPage() {
  const navigate = useNavigate();
  const createProject = useCreateProject();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [areas, setAreas] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [readingLevel, setReadingLevel] = useState<ReadingLevel>("graduate");
  const [allResearchAreas, setAllResearchAreas] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getResearchAreaOptions().then(setAllResearchAreas);
  }, []);

  const isValid = name.trim().length > 0 && areas.length > 0;

  function addKeyword(value: string) {
    const kw = value.trim().replace(/,$/, "");
    if (kw && !keywords.includes(kw)) {
      setKeywords((prev) => [...prev, kw]);
    }
    setKeywordInput("");
  }

  function handleKeywordKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeyword(keywordInput);
    }
  }

  async function handleCreate() {
    if (!isValid || createProject.isPending) return;
    setError(null);
    try {
      const project = await createProject.mutateAsync({
        name: name.trim(),
        description,
        topics: areas,
        keywords,
        readingLevel,
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Create a Project</h1>
      <p className="mt-2 text-sm text-gray-600">
        Set up a focused workspace to organize your research sources and insights.
      </p>

      <section className="mt-8 space-y-4">
        <InputField
          label="Project Name"
          required
          placeholder="e.g. AI Safety Literature Review"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <div className="w-full">
          <label className="mb-1.5 block text-sm font-medium text-gray-900">Description</label>
          <textarea
            placeholder="Briefly describe what this project is about..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-700"
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-900">
          Topics of Interest <span className="text-red-500">*</span>
        </h2>

        <p className="mt-4 text-xs font-semibold text-gray-700">Research Area(s)</p>
        <ResearchAreaPicker
          options={allResearchAreas}
          selected={areas}
          onChange={setAreas}
        />

        <p className="mt-4 text-xs font-semibold text-gray-700">Specific Keywords</p>
        <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 focus-within:border-brand-700 focus-within:ring-1 focus-within:ring-brand-700">
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
            onKeyDown={handleKeywordKeyDown}
            onBlur={() => keywordInput.trim() && addKeyword(keywordInput)}
            className="min-w-[120px] flex-1 border-0 bg-transparent text-sm outline-none"
          />
        </div>
        <p className="mt-1.5 text-xs text-gray-500">Press Enter or comma to add a keyword.</p>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-gray-900">
          Reading Level <span className="text-red-500">*</span>
        </h2>
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
            icon={<Microscope className="h-5 w-5" />}
            title="Expert"
            description="More specific and analytical."
            selected={readingLevel === "expert"}
            onClick={() => setReadingLevel("expert")}
          />
        </div>
      </section>

      {error ? (
        <p className="mt-6 text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-10 flex items-center justify-between border-t border-gray-200 pt-6">
        <Link to="/projects" className="text-sm font-medium text-gray-500 hover:text-gray-700">
          Cancel
        </Link>
        <button
          type="button"
          onClick={() => void handleCreate()}
          disabled={!isValid || createProject.isPending}
          className="rounded-lg px-5 py-2 text-sm font-medium text-white transition-colors enabled:bg-brand-700 enabled:hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {createProject.isPending ? "Creating…" : "Create Project →"}
        </button>
      </div>
    </div>
  );
}
