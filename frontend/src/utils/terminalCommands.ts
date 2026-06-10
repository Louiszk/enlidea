import { AgentDirective } from '../api/generated/api';
import React from 'react';
import { TerminalOutputItem } from '../types';

export interface TerminalCommandContext {
  appendOutput: (text: string, type: 'system' | 'info' | 'error' | 'success') => void;
  setTerminalOutput: React.Dispatch<React.SetStateAction<TerminalOutputItem[]>>;
  appendDirective: (dir: AgentDirective) => void;
  directives: AgentDirective[];
  deleteDirectiveMutation: { mutate: (id: number) => void };
}

export interface TerminalCommand {
  description: string;
  usage?: string;
  execute: (args: string[], context: TerminalCommandContext) => void;
}

export const LOCAL_COMMANDS: Record<string, TerminalCommand> = {
  '/help': {
    description: 'Show this message',
    execute: (args, { appendOutput }) => {
      appendOutput('Available Commands:', 'system');
      Object.entries(LOCAL_COMMANDS).forEach(([cmd, config]) => {
        const usage = config.usage ? ` ${config.usage}` : '';
        const paddedCmd = (cmd + usage).padEnd(20, ' ');
        appendOutput(`  ${paddedCmd} - ${config.description}`, 'info');
      });
      appendOutput('  @<agent> <msg>       - Issue a directive to a specific agent', 'info');
    }
  },
  '/clear': {
    description: 'Clear terminal output visually',
    execute: (args, { setTerminalOutput }) => {
      setTerminalOutput([]);
    }
  },
  '/list': {
    description: 'List directives sequentially (snapshot)',
    usage: '[status]',
    execute: (args, { appendOutput, appendDirective, directives }) => {
      const status = args[0]?.toLowerCase() || 'all';
      
      const filtered = directives.filter(dir => {
        if (status === 'all') return true;
        return dir.status === status;
      });

      if (filtered.length === 0) {
        appendOutput(`[SYSTEM] No ${status} directives found.`, 'info');
        return;
      }

      appendOutput(`[SYSTEM] Listing ${status.toUpperCase()} directives:`, 'system');
      filtered.forEach(dir => {
        appendDirective(dir);
      });
    }
  },
  '/remove': {
    description: 'Remove a pending directive by ID',
    usage: '<id>',
    execute: (args, { appendOutput, directives, deleteDirectiveMutation }) => {
      const dirId = args[0];
      if (!dirId || isNaN(Number(dirId))) {
        appendOutput(`[ERROR] Usage: /remove <id>`, 'error');
      } else {
        const dir = directives.find(d => d.id === parseInt(dirId, 10));
        if (!dir) {
          appendOutput(`[ERROR] Directive #${dirId} not found.`, 'error');
        } else if (dir.status !== 'pending') {
          appendOutput(`[ERROR] Only 'pending' directives can be removed.`, 'error');
        } else {
          deleteDirectiveMutation.mutate(dir.id);
        }
      }
    }
  }
};

export const executeCommand = (cmdStr: string, context: TerminalCommandContext) => {
  const [command, ...args] = cmdStr.trim().split(/\s+/);
  const normalizedCommand = command.toLowerCase();

  const cmdConfig = LOCAL_COMMANDS[normalizedCommand];
  
  if (cmdConfig) {
    cmdConfig.execute(args, context);
  } else {
    context.appendOutput(`[ERROR] Unknown command: ${command}. Type /help for a list of commands.`, 'error');
  }
};
