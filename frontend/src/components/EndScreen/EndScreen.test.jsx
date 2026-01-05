import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EndScreen } from './EndScreen';
import { OUTCOMES, outcomeFor } from './outcomes';
import { STATUS } from '../../config';

const DEBRIEF = {
  turns: [
    { index: 1, player_message: 'Evening mate', score_delta: 6, reasoning: 'Politeness lands.' },
    { index: 2, player_message: 'Here is cash', score_delta: -12, reasoning: 'Costs influence: bribery.' },
  ],
};

const renderEnd = (props = {}) =>
  render(
    <EndScreen
      status={STATUS.ACCESS_GRANTED}
      score={104}
      threshold={100}
      debrief={null}
      onPlayAgain={() => {}}
      {...props}
    />,
  );

describe('EndScreen', () => {
  it('has a distinct screen for each way a run can end', () => {
    expect(Object.keys(OUTCOMES)).toEqual([
      STATUS.ACCESS_GRANTED,
      STATUS.TURNS_EXHAUSTED,
      STATUS.EJECTED,
    ]);
    const titles = new Set(Object.values(OUTCOMES).map((outcome) => outcome.title));
    expect(titles.size).toBe(3);
  });

  it('renders nothing while the run is still in progress', () => {
    expect(outcomeFor(STATUS.IN_PROGRESS)).toBeNull();
    const { container } = renderEnd({ status: STATUS.IN_PROGRESS });
    expect(container).toBeEmptyDOMElement();
  });

  it('announces a win with the final score', () => {
    renderEnd();
    expect(screen.getByText('ACCESS GRANTED')).toBeInTheDocument();
    expect(screen.getByText('104')).toBeInTheDocument();
    expect(screen.getByText('/ 100 influence')).toBeInTheDocument();
  });

  it('announces running out of turns as a loss', () => {
    renderEnd({ status: STATUS.TURNS_EXHAUSTED, score: 71 });
    expect(screen.getByText('THE NIGHT ENDS')).toBeInTheDocument();
  });

  it('announces being ejected', () => {
    renderEnd({ status: STATUS.EJECTED, score: -50 });
    expect(screen.getByText('MOVE ALONG')).toBeInTheDocument();
  });

  it('hides the debrief until the server supplies one', () => {
    renderEnd();
    expect(screen.queryByText(/What Marcus was actually scoring/i)).not.toBeInTheDocument();
  });

  it('reveals the hidden reasoning turn by turn once the run is over', () => {
    renderEnd({ status: STATUS.EJECTED, score: -50, debrief: DEBRIEF });
    expect(screen.getByText(/What Marcus was actually scoring/i)).toBeInTheDocument();
    expect(screen.getByText('Politeness lands.')).toBeInTheDocument();
    expect(screen.getByText('+6')).toBeInTheDocument();
    expect(screen.getByText('-12')).toBeInTheDocument();
  });

  it('offers a way back to a fresh run', async () => {
    const onPlayAgain = vi.fn();
    renderEnd({ onPlayAgain });
    await userEvent.click(screen.getByRole('button', { name: 'Play again' }));
    expect(onPlayAgain).toHaveBeenCalledOnce();
  });
});
