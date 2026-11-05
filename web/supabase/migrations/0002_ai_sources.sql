-- Summaries can now come from any AI provider (Gemini or Claude), so the source
-- names are provider-neutral. The old 'claude' values stay valid for existing rows.
alter table public.nd_reports drop constraint if exists nd_reports_summary_source_check;
alter table public.nd_reports add constraint nd_reports_summary_source_check
  check (summary_source in ('pasted', 'ai', 'ai-challenge', 'claude', 'claude-challenge'));
