'use client';

import React, { Component, ErrorInfo, ReactNode } from "react";
import { DialogInfo } from "@/custom-components/DialogInfo";

interface Props {
  children?: ReactNode;
  /** Name of the component that we're wrapping (used in placeholder text) */
  componentName?: string;
  /** placeholder content */
  placeholder: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  open: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: undefined, open: true };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, open: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught an error", error, info);
  }

  handleOpenChange = (open: boolean) => {
    this.setState({ open });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      const { placeholder, componentName } = this.props;

      return (
        <>
          {/* Dialog showing detailed error */}
          <DialogInfo
            open={this.state.open}
            onOpenChange={this.handleOpenChange}
            title={`Error in ${componentName || "Component"}`}
            description="An error occurred while rendering this section"
            content={
              <div className="space-y-3">
                <div className="text-sm text-red-600 font-mono bg-red-50 rounded-md p-3 border border-red-200">
                  {this.state.error.message}
                </div>
                {this.state.error.stack && (
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto whitespace-pre-wrap">
                    {this.state.error.stack}
                  </pre>
                )}
              </div>
            }
          />

          {/* Layout placeholder */}
          {placeholder ?? (
            <div className="p-4 border border-dashed border-red-400 bg-red-50 text-red-700 text-sm rounded-md min-h-[150px] flex items-center justify-center">
              Failed to load {componentName || "this section"}.
            </div>
          )}
        </>
      );
    }

    return this.props.children;
  }
}
