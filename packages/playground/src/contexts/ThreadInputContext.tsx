import { createContext, useContext, useState, ReactNode } from "react";

interface ThreadInputContextType {
  input: string;
  setInput: (value: string) => void;
  clearInput: () => void;
}

const ThreadInputContext = createContext<ThreadInputContextType | undefined>(
  undefined
);

export function ThreadInputProvider({ children }: { children: ReactNode }) {
  const [input, setInput] = useState("");

  const clearInput = () => setInput("");

  return (
    <ThreadInputContext.Provider value={{ input, setInput, clearInput }}>
      {children}
    </ThreadInputContext.Provider>
  );
}

export function useThreadInput() {
  const context = useContext(ThreadInputContext);
  if (context === undefined) {
    throw new Error("useThreadInput must be used within ThreadInputProvider");
  }
  return context;
}

