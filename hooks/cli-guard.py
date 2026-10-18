#!/usr/bin/env python3
# PreToolUse hook for Bash.
# Asks the user to approve each command that runs a cloud or network CLI from TOOLS, in any
# segment of the command. dcg and its packs cover all other commands.
# Finds the program of each segment after ; && || | & ( ) and newlines outside quotes. Skips
# variable assignments, wrappers such as sudo, env, command, exec, xargs, and timeout, and
# directory paths, shell keywords such as do and then, and flags of wrappers, with their values.
# Looks inside bash -c / sh -c strings, eval, $( ), and backticks.
# A heredoc body is data, unless a shell reads it (bash <<EOF, cat <<EOF | sh).
# A shell that reads commands from a pipe or stdin asks when a TOOLS word appears anywhere.
# A here-string to a shell (bash <<< '...'), a bash -c or eval body with a $ expansion, or a
# program that is a variable ($CMD) asks when a TOOLS word appears anywhere.
# If the command cannot be parsed, asks when a TOOLS word appears anywhere (fail closed).
# Other commands get no decision.

import json
import re
import shlex
import sys
from pathlib import PurePosixPath

TOOLS = {"az", "sf", "sfdx", "curl", "wget", "http", "https", "xh"}
WRAPPERS = {"sudo", "doas", "env", "command", "exec", "nohup", "time", "nice", "xargs", "timeout", "caffeinate"}
SHELLS = {"bash", "sh", "zsh", "dash"}
KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "}"}
# Wrapper flags that take the next word as their value.
VALUE_FLAGS = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "--user", "--group"},
    "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-P", "--unset", "--chdir"},
    "exec": {"-a"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-J", "-L", "-n", "-P", "-s", "-d", "-E", "-R", "-S"},
    "nice": {"-n"},
    "caffeinate": {"-t", "-w"},
}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "()", ";;", "|&"}
# Shell operators, longest first, to split runs such as ";(" that shlex returns as one token.
OPERATORS = ["&&", "||", ";;", "|&", "()", ";", "&", "|", "(", ")"]
# Shell options that take the next word as their value.
SHELL_VALUE_FLAGS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
DURATION = re.compile(r"^\d+(?:\.\d+)?[smhd]?$")
# A redirect operator alone (its target is the next word), or with its target attached.
REDIRECT = re.compile(r"^\d*(?:[<>]{1,3}|&>>?|>&|<&)$")
REDIRECT_ATTACHED = re.compile(r"^\d*(?:[<>]{1,3}|&>>?|>&|<&)\S")
TOOL_WORD = re.compile(r"(?<![\w.-])(" + "|".join(sorted(TOOLS)) + r")(?![\w.:/-])")
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
SHELL_AFTER = re.compile(r"\|\s*(?:" + "|".join(sorted(SHELLS)) + r")\b")
SHELL_BEFORE = re.compile(r"(?:^|[\s;&|(])(?:" + "|".join(sorted(SHELLS)) + r")(?:\s+-\S+)*\s*$")


def outside_quotes(text):
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote == "'":
            quote = None if c == "'" else quote
        elif c == "\\":
            i += 1
        elif c in "'\"":
            quote = None if quote == c else (quote or c)
        i += 1
    return quote is None


def strip_heredocs(command):
    """Drops heredoc bodies, except bodies that a shell reads as commands."""
    out, lines, i = [], command.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for match in HEREDOC.finditer(line):
            if not outside_quotes(line[: match.start()]):
                continue
            body = []
            while i < len(lines) and lines[i].strip() != match.group(2):
                body.append(lines[i])
                i += 1
            closed = i < len(lines)
            i += 1
            shell = SHELL_BEFORE.search(line[: match.start()]) or SHELL_AFTER.search(line[match.end() :])
            if shell or not closed:
                out.extend(body)
    return "\n".join(out)


def scan(command):
    """Returns the command with unquoted newlines as ';', and the bodies of $( ) and backticks."""
    out, inner, quote, i = [], [], None, 0
    while i < len(command):
        c = command[i]
        if quote == "'":
            quote = None if c == "'" else quote
        elif c == "\\" and i + 1 < len(command):
            out.append(command[i : i + 2])
            i += 2
            continue
        elif quote == '"' and c == '"':
            quote = None
        elif quote is None and c in "'\"":
            quote = c
        elif quote is None and c == "\n":
            c = ";"
        if quote != "'" and command.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(command) and depth:
                depth += {"(": 1, ")": -1}.get(command[j], 0)
                j += 1
            inner.append(command[i + 2 : j - 1])
        elif quote != "'" and c == "`":
            end = command.find("`", i + 1)
            if end > i:
                inner.append(command[i + 1 : end])
                out.append(command[i : end + 1])
                i = end + 1
                continue
        out.append(c)
        i += 1
    return "".join(out), inner


def program(segment):
    i, wrapper = 0, None
    while i < len(segment):
        word = segment[i]
        name = PurePosixPath(word).name
        if word == "function":
            i += 2
        elif word in KEYWORDS or ASSIGNMENT.match(word) or DURATION.match(word):
            i += 1
        elif wrapper == "env" and word in {"-S", "--split-string"} and i + 1 < len(segment):
            try:
                return program(shlex.split(segment[i + 1]) + segment[i + 2 :])
            except ValueError:
                return None, []
        elif word.startswith("-"):
            i += 2 if word in VALUE_FLAGS.get(wrapper, ()) else 1
        elif name in WRAPPERS:
            wrapper = name
            i += 1
        else:
            return name, segment[i + 1 :]
    return None, []


def shell_flag_c(arg):
    return re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", arg) is not None


def script_args(args):
    """Returns the shell arguments that are not flags or redirects, such as a script file.
    After -s, the shell reads commands from stdin, and the rest are positional arguments."""
    out, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif re.fullmatch(r"-[A-Za-z]*s[A-Za-z]*", arg):
            break
        elif REDIRECT.match(arg) or arg in SHELL_VALUE_FLAGS or re.fullmatch(r"[-+][A-Za-z]*[oO][A-Za-z]*", arg):
            skip = True
        elif not arg.startswith(("-", "+")) and not REDIRECT_ATTACHED.match(arg):
            out.append(arg)
    return out


def split_operators(word):
    """Splits a run of shell punctuation, such as ";(" or ")&&", into separate operators."""
    if not word or any(c not in ";&|()" for c in word):
        return [word]
    parts = []
    while word:
        op = next(op for op in OPERATORS if word.startswith(op))
        parts.append(op)
        word = word[len(op) :]
    return parts


def found(command, depth=0):
    if depth > 5:
        return set()
    flat, inner = scan(strip_heredocs(command))
    hits = set()
    for body in inner:
        hits |= found(body, depth + 1)
    try:
        lexer = shlex.shlex(flat, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        words = [part for word in lexer for part in split_operators(word)]
    except ValueError:
        return hits | set(TOOL_WORD.findall(flat))
    segment = []
    for word in words + [";"]:
        if word not in SEPARATORS:
            segment.append(word)
            continue
        name, args = program(segment)
        segment = []
        if name in TOOLS:
            hits.add(name)
        elif name and name.startswith("$"):
            hits |= set(TOOL_WORD.findall(command))
        elif name in SHELLS:
            flag = next((j for j, arg in enumerate(args) if shell_flag_c(arg)), None)
            here = [args[j + 1] for j, arg in enumerate(args[:-1]) if arg == "<<<"]
            here += [arg[3:] for arg in args if arg.startswith("<<<") and len(arg) > 3]
            if flag is not None and flag + 1 < len(args):
                hits |= found(args[flag + 1], depth + 1)
                if "$" in args[flag + 1]:
                    hits |= set(TOOL_WORD.findall(command))
            elif here:
                hits |= set(TOOL_WORD.findall(command))
            elif not script_args(args):
                hits |= set(TOOL_WORD.findall(command))
        elif name == "eval":
            hits |= found(" ".join(args), depth + 1)
            if any("$" in arg for arg in args):
                hits |= set(TOOL_WORD.findall(command))
    return hits


def main():
    try:
        command = json.load(sys.stdin)["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return
    if not isinstance(command, str) or not TOOL_WORD.search(command):
        return
    hits = found(command)
    if hits:
        names = ", ".join(f"`{h}`" for h in sorted(hits))
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"cli-guard: this command runs {names}.",
            }
        }))


if __name__ == "__main__":
    main()
