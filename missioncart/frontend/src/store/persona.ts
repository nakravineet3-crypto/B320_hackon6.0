import { create } from 'zustand'

export interface Persona {
  id: string
  label: string
  emoji: string
  color: string
}

export const ALL_PERSONAS: Persona[] = [
  { id: 'fitness', label: 'Fitness', emoji: '💪', color: '#E8F5E9' },
  { id: 'dad', label: 'Dad', emoji: '👨', color: '#E3F2FD' },
  { id: 'mom', label: 'Mom', emoji: '👩', color: '#FCE4EC' },
  { id: 'swimmer', label: 'Swimmer', emoji: '🏊', color: '#E0F7FA' },
  { id: 'gamer', label: 'Gamer', emoji: '🎮', color: '#EDE7F6' },
  { id: 'cook', label: 'Cook', emoji: '👨‍🍳', color: '#FFF3E0' },
  { id: 'student', label: 'Student', emoji: '📚', color: '#F3E5F5' },
  { id: 'runner', label: 'Runner', emoji: '🏃', color: '#E8F5E9' },
  { id: 'yogi', label: 'Yogi', emoji: '🧘', color: '#FFF8E1' },
  { id: 'pet-parent', label: 'Pet Parent', emoji: '🐾', color: '#EFEBE9' },
  { id: 'traveler', label: 'Traveler', emoji: '✈️', color: '#E8EAF6' },
  { id: 'cyclist', label: 'Cyclist', emoji: '🚴', color: '#E0F2F1' },
  { id: 'reader', label: 'Reader', emoji: '📖', color: '#FBE9E7' },
  { id: 'gardener', label: 'Gardener', emoji: '🌱', color: '#E8F5E9' },
  { id: 'artist', label: 'Artist', emoji: '🎨', color: '#FCE4EC' },
  { id: 'musician', label: 'Musician', emoji: '🎵', color: '#EDE7F6' },
  { id: 'photographer', label: 'Photographer', emoji: '📷', color: '#ECEFF1' },
  { id: 'hiker', label: 'Hiker', emoji: '🥾', color: '#E8F5E9' },
  { id: 'baker', label: 'Baker', emoji: '🧁', color: '#FFF3E0' },
  { id: 'new-parent', label: 'New Parent', emoji: '👶', color: '#F3E5F5' },
]

interface PersonaStore {
  selectedPersonas: string[]
  togglePersona: (id: string) => void
  isSelected: (id: string) => boolean
}

export const usePersonaStore = create<PersonaStore>((set, get) => ({
  selectedPersonas: ['fitness', 'dad', 'swimmer', 'cook', 'runner'],
  togglePersona: (id: string) => {
    const current = get().selectedPersonas
    if (current.includes(id)) {
      set({ selectedPersonas: current.filter((p) => p !== id) })
    } else {
      set({ selectedPersonas: [...current, id] })
    }
  },
  isSelected: (id: string) => get().selectedPersonas.includes(id),
}))
