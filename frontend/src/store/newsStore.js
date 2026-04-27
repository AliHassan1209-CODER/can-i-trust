import { create } from 'zustand'

export const useNewsStore = create((set) => ({
  articles:    [],
  category:    'general',
  loading:     false,
  searched:    false,
  searchQuery: '',

  setArticles:    (articles)    => set({ articles }),
  setCategory:    (category)    => set({ category }),
  setLoading:     (loading)     => set({ loading }),
  setSearched:    (searched)    => set({ searched }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
}))
