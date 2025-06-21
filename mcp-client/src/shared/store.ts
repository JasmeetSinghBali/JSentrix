import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface WsAuthState {
  clientId: string | null;
  token: string | null;
  setAuth: (clientId: string, token: string) => void;
  clearAuth: ()=> void;
}

export const useWsAuthStore = create<WsAuthState>()(
   persist(
    (set) => ({
      clientId: null,
      token: null,
      setAuth: (clientId,token)=>set({clientId,token}),
      clearAuth: ()=> set({clientId: null, token: null})
    }),
    {
      name: 'auth-storage' // key in localStorage
    }
   )
);