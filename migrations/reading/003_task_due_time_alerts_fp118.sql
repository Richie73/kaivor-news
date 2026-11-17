-- FP118: task due time + alert tracking.
-- Additive and safe to rerun. Run in the Supabase SQL Editor
-- (project KaivorDatabase) before the FP118 code is installed.
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS due_time TIME;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS alerted_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_tasks_due_alert
  ON public.tasks (done, due_date, due_time)
  WHERE alerted_at IS NULL;
