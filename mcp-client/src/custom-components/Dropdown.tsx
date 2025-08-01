'use client'
// custom-components/Dropdown.tsx
import * as React from "react";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

export interface DropdownOption {
  label: string;
  value: string;
}

interface DropdownProps {
  label?: string;
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  buttonClassName?: string;
  menuClassName?: string;
  disabled?: boolean;
}

const Dropdown: React.FC<DropdownProps> = ({
  label,
  options,
  value,
  onChange,
  buttonClassName,
  menuClassName,
  disabled,
}) => {
  const selected = options.find(opt => opt.value === value);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button disabled={disabled || false} variant="outline" className={buttonClassName || "w-[210px] justify-between"}>
          {selected ? selected.label : "Select..."}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className={menuClassName || "w-56"}>
        {label && <DropdownMenuLabel>{label}</DropdownMenuLabel>}
        <DropdownMenuRadioGroup value={value} onValueChange={onChange}>
          {options.map(opt => (
            <DropdownMenuRadioItem key={opt.value} value={opt.value}>
              {opt.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default Dropdown;
