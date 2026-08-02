# AGENTS.md · the SoulOS engine master

1. This repo is the ONLY master of the engine: template/, scripts/new_estate.sh, INTERVIEW.md. The application layer keeps a synced copy at ../soulos/engine/; never edit copies.
2. Plain voice in every doc: no em dashes, no en dashes, no curly quotes, no AI-tell filler. The template ships these rules to strangers; the repo must live by them too.
3. Changes to the template must keep the stamp runnable end to end (clone, stamp, interview, seal). Test before calling it done.
4. End every file-changing session by telling the owner the seal is due: bash ~/dev/soulos/scripts/seal_soulos.sh "what changed" (it syncs this engine into the application layer first, then pushes both).
