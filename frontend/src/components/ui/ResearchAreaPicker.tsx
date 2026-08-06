import { type KeyboardEvent, useMemo, useRef, useState } from "react";

import { Tag } from "@/components/ui/Tag";

interface ResearchAreaPickerProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

export function ResearchAreaPicker({ options, selected, onChange }: ResearchAreaPickerProps) {
  const [customOptions, setCustomOptions] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [topicInput, setTopicInput] = useState("");
  const skipBlurCommit = useRef(false);

  const displayOptions = useMemo(() => {
    const seen = new Set<string>();
    const merged: string[] = [];
    for (const area of [...options, ...customOptions, ...selected]) {
      if (!seen.has(area)) {
        seen.add(area);
        merged.push(area);
      }
    }
    return merged;
  }, [options, customOptions, selected]);

  function toggleArea(area: string) {
    onChange(
      selected.includes(area) ? selected.filter((a) => a !== area) : [...selected, area],
    );
  }

  function cancelAdding() {
    skipBlurCommit.current = true;
    setAdding(false);
    setTopicInput("");
  }

  function commitTopic(value: string) {
    const topic = value.trim().replace(/,$/, "");
    if (!topic) {
      cancelAdding();
      return;
    }

    if (!options.includes(topic) && !customOptions.includes(topic)) {
      setCustomOptions((prev) => [...prev, topic]);
    }
    if (!selected.includes(topic)) {
      onChange([...selected, topic]);
    }
    skipBlurCommit.current = true;
    setAdding(false);
    setTopicInput("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commitTopic(topicInput);
    } else if (e.key === "Escape") {
      e.preventDefault();
      cancelAdding();
    }
  }

  function handleBlur() {
    if (skipBlurCommit.current) {
      skipBlurCommit.current = false;
      return;
    }
    commitTopic(topicInput);
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      {displayOptions.map((area) => (
        <button key={area} type="button" onClick={() => toggleArea(area)}>
          <Tag variant={selected.includes(area) ? "brand" : "outline"}>{area}</Tag>
        </button>
      ))}
      {adding ? (
        <input
          type="text"
          autoFocus
          placeholder="New topic..."
          value={topicInput}
          onChange={(e) => setTopicInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          className="min-w-[120px] rounded-full border border-gray-300 px-2.5 py-0.5 text-xs outline-none focus:border-brand-700 focus:ring-1 focus:ring-brand-700"
        />
      ) : (
        <button type="button" onClick={() => setAdding(true)}>
          <Tag variant="outline">Add Topic +</Tag>
        </button>
      )}
    </div>
  );
}
