insert into storage.buckets (id, name, public)
values ('npcs', 'npcs', false)
on conflict (id) do nothing;

-- Objects are stored as {user_id}/{slug}/..., so the first path segment is
-- the owner. The backend currently reaches this bucket via the S3-compatible
-- API using project-level access keys, which bypasses these policies
-- entirely - they're defense in depth for if the bucket is ever accessed
-- from the frontend with the anon key instead.
drop policy if exists "npcs: users manage their own objects" on storage.objects;

create policy "npcs: users manage their own objects"
    on storage.objects
    for all
    to authenticated
    using (bucket_id = 'npcs' and (storage.foldername(name))[1] = auth.uid()::text)
    with check (bucket_id = 'npcs' and (storage.foldername(name))[1] = auth.uid()::text);
