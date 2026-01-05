import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from './ChatInput';
import { STATUS } from '../config';

const renderInput = (props = {}) =>
  render(
    <ChatInput
      onSend={() => {}}
      isLoading={false}
      disabled={false}
      status={STATUS.IN_PROGRESS}
      {...props}
    />,
  );

describe('ChatInput', () => {
  it('sends the trimmed line and clears itself', async () => {
    const onSend = vi.fn();
    renderInput({ onSend });
    const field = screen.getByRole('textbox');

    await userEvent.type(field, '  evening mate  {Enter}');
    expect(onSend).toHaveBeenCalledWith('evening mate');
    expect(field).toHaveValue('');
  });

  it('will not send whitespace', async () => {
    const onSend = vi.fn();
    renderInput({ onSend });
    await userEvent.type(screen.getByRole('textbox'), '   {Enter}');
    expect(onSend).not.toHaveBeenCalled();
  });

  it('locks while Marcus is thinking', () => {
    renderInput({ isLoading: true });
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('caps the message length the server would truncate anyway', () => {
    renderInput();
    expect(screen.getByRole('textbox')).toHaveAttribute('maxLength', '500');
  });

  it.each([
    [STATUS.ACCESS_GRANTED, /enjoy the room/i],
    [STATUS.TURNS_EXHAUSTED, /queue has moved on/i],
    [STATUS.EJECTED, /not listening/i],
  ])('explains why the box is closed after %s', (status, copy) => {
    renderInput({ status, disabled: true });
    expect(screen.getByRole('textbox')).toHaveAttribute('placeholder', expect.stringMatching(copy));
  });

  it('prompts for a line while the run is live', () => {
    renderInput();
    expect(screen.getByRole('textbox')).toHaveAttribute(
      'placeholder',
      'What do you say to the doorman?',
    );
  });
});
