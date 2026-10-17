import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw, Home, Compass } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
  onSwitchToDefaultProject?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('TerraShield AI ErrorBoundary caught an exception:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public handleFallback = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onSwitchToDefaultProject) {
      this.props.onSwitchToDefaultProject();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-4xl mx-auto my-12 p-8 rounded-3xl bg-terra-forest/40 border border-rose-500/30 backdrop-blur-xl shadow-2xl space-y-6 animate-fade-in text-terra-ivory">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/30 shrink-0">
              <AlertCircle className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-widest text-rose-400 font-bold">
                Application Rendering Safeguard
              </span>
              <h2 className="text-xl sm:text-2xl font-display font-semibold text-terra-ivory">
                {this.props.fallbackTitle || 'Project View Encountered an Unexpected Issue'}
              </h2>
              <p className="text-sm text-terra-muted leading-relaxed">
                TerraShield AI preserved the application shell and prevented the interface from
                becoming unresponsive. The selected project or workspace data could not be rendered
                with the current configuration.
              </p>
            </div>
          </div>

          {this.state.error && (
            <div className="p-4 rounded-xl bg-terra-deep/80 border border-terra-border/50 text-xs font-mono text-rose-300 overflow-x-auto">
              <div className="font-bold text-terra-slate mb-1">Exception Details:</div>
              {this.state.error.name}: {this.state.error.message}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={this.handleReset}
              className="px-5 py-2.5 rounded-xl bg-terra-mint text-terra-deep font-semibold text-xs hover:bg-terra-mint/90 transition flex items-center gap-2 cursor-pointer shadow-lg shadow-terra-mint/10"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retry Active View</span>
            </button>

            {this.props.onSwitchToDefaultProject && (
              <button
                onClick={this.handleFallback}
                className="px-5 py-2.5 rounded-xl bg-terra-forest/80 hover:bg-terra-forest text-terra-ivory font-semibold text-xs border border-terra-border/60 transition flex items-center gap-2 cursor-pointer"
              >
                <Compass className="w-4 h-4 text-terra-mint" />
                <span>Return to Wayanad Pilot (Demo)</span>
              </button>
            )}

            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 rounded-xl bg-terra-forest/40 hover:bg-terra-forest/70 text-terra-muted hover:text-terra-ivory font-semibold text-xs border border-terra-border/40 transition flex items-center gap-2 cursor-pointer"
            >
              <Home className="w-4 h-4 text-terra-slate" />
              <span>Reload Application Session</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
