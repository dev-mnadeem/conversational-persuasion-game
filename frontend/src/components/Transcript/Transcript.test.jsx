import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Transcript } from './Transcript';

const MESSAGES = [
  { id: 1, role: 'user', content: 'Evening mate, how long have you worked here?' },
  { id: 2, role: 'assistant', content: 'Eight years. Nobody has asked since March.' },
];

describe('Transcript', () => {
  it('coaches the player instead of showing an empty box', () => {
    render(<Transcript messages={[]} isThinking={false} turnsUsed={0} maxTurns={12} />);
    expect(screen.getByText(/Marcus has not looked up yet/i)).toBeInTheDocument();
    expect(screen.getByText(/Money, names and impatience/i)).toBeInTheDocument();
  });

  it('keeps the whole exchange visible, not just the latest line', () => {
    render(<Transcript messages={MESSAGES} isThinking={false} turnsUsed={1} maxTurns={12} />);
    expect(screen.getByText(MESSAGES[0].content)).toBeInTheDocument();
    expect(screen.getByText(MESSAGES[1].content)).toBeInTheDocument();
  });

  it('attributes each line to a speaker', () => {
    render(<Transcript messages={MESSAGES} isThinking={false} turnsUsed={1} maxTurns={12} />);
    expect(screen.getByText('YOU')).toBeInTheDocument();
    expect(screen.getByText('MARCUS')).toBeInTheDocument();
  });

  it('shows how much of the turn budget is gone', () => {
    render(<Transcript messages={MESSAGES} isThinking={false} turnsUsed={4} maxTurns={12} />);
    expect(screen.getByText('TURN 4 / 12')).toBeInTheDocument();
  });

  it('counts the in-flight turn while Marcus is thinking', () => {
    render(<Transcript messages={MESSAGES} isThinking turnsUsed={4} maxTurns={12} />);
    expect(screen.getByText('TURN 5 / 12')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/sizing you up/i);
  });

  it('never counts past the budget', () => {
    render(<Transcript messages={MESSAGES} isThinking turnsUsed={12} maxTurns={12} />);
    expect(screen.getByText('TURN 12 / 12')).toBeInTheDocument();
  });
});
