---
name: dotenvx
description: Rules to encrypt .env files and redact secrets in command output with dotenvx. Use when a project has a .env file, needs an API key or other secret, or when you add, read, or change environment variables.
---

# dotenvx

These rules apply to dotenvx v2.38.0.
The goal is to keep `.env` files encrypted and secret values out of command output.

## Use secrets

- Run each command that needs a secret with this form only:
  `dotenvx run --redact -- <command>`.
- `--redact` replaces each injected value with `[REDACTED]` in stdout and stderr.
  The command still gets the real values.
- `--redact` finds only exact values.
  An encoded, split, or partial value can still go into the output.
- Do not ask the user to start Claude with `dotenvx run -- claude`.
  Then each secret is in the environment of each Bash call, and any command can print it.

## Read a secret

- Do not run `dotenvx decrypt` or `dotenvx get`. Do not read, print, or store a decrypted value.
  When a command needs one, use `dotenvx run --redact -- <command>`.
  - `decrypt` writes the plain values back into the `.env` file, which can then be committed.
  - `get` prints the plain value.
- When the user needs to see a decrypted value, tell them to run `dotenvx get <KEY>` in their own terminal.
  Do not suggest `! dotenvx get <KEY>`. The output of a `!` command goes into the transcript.
- Do not ask the user to paste or type the value into the chat. Ask only whether it is correct.
- Do not suggest `dotenvx decrypt` to the user.

## Add or change secrets

- Do not put a secret value in a command, a file, or a message.
- Ask the user to add the value to `.env` in an editor, then run `dotenvx encrypt`.
- Do not suggest `! dotenvx set <KEY> <value>`.
  The `!` command and its value go into the transcript.

## Encrypt and commit

- Encrypt each `.env` file with `dotenvx encrypt -f <file>`.
  dotenvx writes the private key to `.env.keys`.
- Before each commit, run `dotenvx encrypt -f <file>` again on each env file.
  It encrypts each plain value and prints no value.
  When all values are encrypted, it prints `no change`.
- Commit the encrypted `.env` file.
- Do not commit `.env.keys`. Make sure that `.gitignore` has `.env.keys`.
- For a new project, put the `.env.keys` value in a password manager or the CI secret store.
