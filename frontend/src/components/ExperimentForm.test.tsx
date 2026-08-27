import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ExperimentForm } from './ExperimentForm'

const scenarios = [
  { id: 'echo' as const, label: 'Controlled output', description: 'Echo data.', expected_outcome: 'success' },
  { id: 'sleep' as const, label: 'Controlled service time', description: 'Wait safely.', expected_outcome: 'success' },
]

describe('ExperimentForm', () => {
  it('submits the selected deterministic parameters', async () => {
    const onRun = vi.fn().mockResolvedValue(undefined)
    render(<ExperimentForm scenarios={scenarios} busy={false} onRun={onRun} />)
    fireEvent.change(screen.getByLabelText('Scenario'), { target: { value: 'sleep' } })
    fireEvent.change(screen.getByLabelText('Repetitions'), { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Seed'), { target: { value: '17' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run experiment' }))
    expect(onRun).toHaveBeenCalledWith({ scenario: 'sleep', repeat: 4, seed: 17 })
    expect(screen.getByTestId('scenario-description')).toHaveTextContent('Wait safely.')
  })
})
