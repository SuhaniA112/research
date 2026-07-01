import { NavLink } from "react-router-dom";
import {
  ChevronDown,
  ChevronUp,
  FolderOpen,
  Home,
  PanelLeft,
  Plus,
  Search,
} from "lucide-react";
import { useState } from "react";

import { env } from "@/config/env";
import { currentUser, projects, recentProjectSearches } from "@/data/mockData";
import { getFindSourcesPath } from "@/lib/sourcePaths";

const exploreLinks = [
  { to: "/hub", label: "Hub", icon: Home },
  { to: "/projects", label: "All Projects", icon: FolderOpen, end: true },
  { to: "/projects/new", label: "New Project", icon: Plus },
  { to: "/searches", label: "Recent Searches", icon: Search },
];

const sidebarShell =
  "flex h-screen shrink-0 flex-col overflow-hidden border-r border-gray-200 bg-surface-sidebar";

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [expandedProject, setExpandedProject] = useState("4");

  if (collapsed) {
    return (
      <aside className={`${sidebarShell} w-14 items-center py-4`}>
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="mb-6 rounded-lg p-2 text-gray-600 hover:bg-gray-200"
        >
          <PanelLeft className="h-5 w-5" />
        </button>
        <nav className="flex flex-col items-center">
          {exploreLinks.map(({ to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `mb-2 rounded-lg p-2 ${isActive ? "bg-gray-200 text-brand-700" : "text-gray-600 hover:bg-gray-200"}`
              }
            >
              <Icon className="h-5 w-5" />
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto">
          <NavLink to="/profile" className="block rounded-full bg-brand-700 p-2">
            <span className="flex h-6 w-6 items-center justify-center text-xs font-bold text-white">
              {currentUser.name[0]}
            </span>
          </NavLink>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`${sidebarShell} w-60`}>
      <div className="flex shrink-0 items-center justify-between px-4 py-4">
        <span className="text-sm font-bold text-gray-900">{env.appName}</span>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="rounded p-1 text-gray-500 hover:bg-gray-200"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-3">
        <p className="mb-2 shrink-0 px-2 text-xs font-semibold tracking-wide text-gray-500">
          EXPLORE
        </p>
        <nav className="shrink-0 space-y-0.5">
          {exploreLinks.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm ${
                  isActive
                    ? "bg-gray-200 font-medium text-gray-900"
                    : "text-gray-600 hover:bg-gray-100"
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <p className="mb-2 mt-6 shrink-0 px-2 text-xs font-semibold tracking-wide text-gray-500">
          RECENT PROJECTS
        </p>
        <div className="min-h-0 flex-1 overflow-hidden">
          <div className="space-y-0.5">
            {projects.map((project) => {
              const isExpanded = expandedProject === project.id;
              const searches = recentProjectSearches[project.id] ?? [];
              return (
                <div key={project.id}>
                  <button
                    type="button"
                    onClick={() => setExpandedProject(isExpanded ? "" : project.id)}
                    className="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    <NavLink
                      to={`/projects/${project.id}`}
                      className="flex-1 truncate text-left hover:text-brand-700"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {project.name}
                    </NavLink>
                    {isExpanded ? (
                      <ChevronUp className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                    )}
                  </button>
                  {isExpanded && searches.length > 0 && (
                    <div className="ml-4 space-y-0.5 border-l border-gray-200 pl-2">
                      {searches.map((search) => (
                        <NavLink
                          key={search}
                          to={getFindSourcesPath(project.id, search)}
                          className="block truncate px-2 py-1 text-xs text-gray-500 hover:text-brand-700"
                        >
                          {search}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t border-gray-200 p-4">
        <NavLink to="/profile" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-700 text-sm font-bold text-white">
            {currentUser.name[0]}
          </div>
          <span className="truncate text-sm font-medium text-gray-900">
            {currentUser.fullName}
          </span>
        </NavLink>
      </div>
    </aside>
  );
}
