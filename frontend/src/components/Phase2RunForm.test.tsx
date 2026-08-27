import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Phase2RunForm } from './Phase2RunForm'

describe('Phase2RunForm', () => {
  it('submits controlled transport factors', () => {
    const onRun = vi.fn().mockResolvedValue(undefined)
    render(<Phase2RunForm busy={false} onRun={onRun} />)
    fireEvent.change(screen.getByLabelText('Transport'), { target: { value: 'in_memory' } })
    fireEvent.change(screen.getByLabelText('Payload size'), { target: { value: '16384' } })
    fireEvent.change(screen.getByLabelText('Service time'), { target: { value: '100' } })
    fireEvent.change(screen.getByLabelText('Concurrency'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Run controlled experiment' }))
    expect(onRun).toHaveBeenCalledWith(expect.objectContaining({ transport: 'in_memory', payload_target_bytes: 16384, service_time_ms: 100, concurrency: 4 }))
  })
})
