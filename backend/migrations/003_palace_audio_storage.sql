-- Palace Audio Storage: Supabase Storage bucket + RLS policies
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)

-- Create the storage bucket (skip if already created via API)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'palace-audio',
  'palace-audio',
  false,
  26214400,  -- 25 MB
  ARRAY['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm']
)
ON CONFLICT (id) DO NOTHING;

-- Drop existing policies if re-running
DROP POLICY IF EXISTS "Users can upload own audio" ON storage.objects;
DROP POLICY IF EXISTS "Users can read own audio" ON storage.objects;
DROP POLICY IF EXISTS "Users can update own audio" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own audio" ON storage.objects;

-- INSERT: user can upload to their own folder ({user_id}/...)
CREATE POLICY "Users can upload own audio" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'palace-audio'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- SELECT: user can download from their own folder
CREATE POLICY "Users can read own audio" ON storage.objects
  FOR SELECT TO authenticated
  USING (
    bucket_id = 'palace-audio'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- UPDATE: user can overwrite files in their own folder
CREATE POLICY "Users can update own audio" ON storage.objects
  FOR UPDATE TO authenticated
  USING (
    bucket_id = 'palace-audio'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );

-- DELETE: user can delete files in their own folder
CREATE POLICY "Users can delete own audio" ON storage.objects
  FOR DELETE TO authenticated
  USING (
    bucket_id = 'palace-audio'
    AND auth.uid()::text = (storage.foldername(name))[1]
  );
