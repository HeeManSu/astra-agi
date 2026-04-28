import { useState, useEffect } from "react";
import { useUpdateToolMutation } from "@/api/rtkApi";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Wrench, Save, FileJson, Check, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { Tool } from "@/types/api";

interface ToolDetailDialogProps {
  tool: Tool | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave?: () => void;
}

type DialogTab = "definition";

function validateJson(json: string): boolean {
  if (!json || json.trim() === "") return true;
  try {
    JSON.parse(json);
    return true;
  } catch {
    return false;
  }
}

function safeParseJsonObject(json: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(json);
    if (parsed && typeof parsed === "object") {
      return parsed as Record<string, unknown>;
    }
    return {};
  } catch {
    return {};
  }
}

function getFieldCount(schema: Record<string, unknown>): number {
  const props = schema.properties;
  if (!props || typeof props !== "object") return 0;
  return Object.keys(props).length;
}

function getRequiredCount(schema: Record<string, unknown>): number {
  const required = schema.required;
  return Array.isArray(required) ? required.length : 0;
}

function ToolDetailDialog({
  tool,
  open,
  onOpenChange,
  onSave,
}: ToolDetailDialogProps) {
  const [updateTool, { isLoading: saving }] = useUpdateToolMutation();

  const [activeTab, setActiveTab] = useState<DialogTab>("definition");
  const [jsonValid, setJsonValid] = useState(true);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [inputSchemaJson, setInputSchemaJson] = useState("");
  const [outputSchemaJson, setOutputSchemaJson] = useState("");

  // Reset the local form state whenever a different tool is opened in the
  // dialog. Using an effect (rather than a `key` reset on the parent) keeps
  // the dialog mounted across selections so the close animation runs.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (tool) {
      setName(tool.name);
      setDescription(tool.description ?? "");
      setInputSchemaJson(JSON.stringify(tool.input_schema ?? {}, null, 2));
      setOutputSchemaJson(JSON.stringify(tool.output_schema ?? {}, null, 2));
      setActiveTab("definition");
      setJsonValid(true);
    }
  }, [tool]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleInputSchemaChange = (value: string) => {
    setInputSchemaJson(value);
    setJsonValid(validateJson(value) && validateJson(outputSchemaJson));
  };

  const handleOutputSchemaChange = (value: string) => {
    setOutputSchemaJson(value);
    setJsonValid(validateJson(inputSchemaJson) && validateJson(value));
  };

  const handleSave = async () => {
    if (!tool) return;
    if (!jsonValid) {
      toast.error("Please fix JSON syntax errors before saving");
      return;
    }

    try {
      const inputSchema = inputSchemaJson
        ? (JSON.parse(inputSchemaJson) as Record<string, unknown>)
        : undefined;
      const outputSchema = outputSchemaJson
        ? (JSON.parse(outputSchemaJson) as Record<string, unknown>)
        : undefined;

      await updateTool({
        slug: tool.slug,
        data: {
          name,
          description,
          ...(inputSchema ? { input_schema: inputSchema } : {}),
          ...(outputSchema ? { output_schema: outputSchema } : {}),
        },
      }).unwrap();
      toast.success("Tool updated successfully");
      onSave?.();
    } catch (error) {
      console.error("Failed to update tool:", error);
      toast.error("Failed to update tool");
    }
  };

  const inputSchema = safeParseJsonObject(inputSchemaJson);
  const outputSchema = safeParseJsonObject(outputSchemaJson);

  if (!tool) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] w-[95vw] h-[90vh] p-0 gap-0 flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div className="flex items-center gap-3">
            <Wrench className="h-5 w-5" />
            <div>
              <h2 className="text-lg font-semibold">{tool.name}</h2>
              <p className="text-sm text-muted-foreground line-clamp-1 max-w-2xl">
                {tool.description || "No description"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 pr-8">
            <Button onClick={handleSave} disabled={saving || !jsonValid}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="w-48 border-r bg-muted/30 flex flex-col shrink-0">
            <nav className="p-2 space-y-1">
              <button
                onClick={() => setActiveTab("definition")}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors",
                  activeTab === "definition"
                    ? "bg-background shadow-sm font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/50",
                )}
              >
                <FileJson className="h-4 w-4" />
                Definition
              </button>
              <button
                disabled
                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md text-muted-foreground/50 cursor-not-allowed"
              >
                <span className="h-4 w-4 text-xs">⚙</span>
                Builder
                <span className="text-[10px] ml-auto">Soon</span>
              </button>
            </nav>
          </div>

          <div className="flex-1 flex overflow-hidden">
            {activeTab === "definition" && (
              <div className="flex-1 flex">
                <div className="flex-1 flex flex-col border-r">
                  <div className="px-4 py-2 border-b flex items-center justify-between bg-muted/30 shrink-0">
                    <span className="text-sm font-medium">Editor</span>
                    <span
                      className={cn(
                        "text-xs flex items-center gap-1",
                        jsonValid ? "text-green-600" : "text-destructive",
                      )}
                    >
                      {jsonValid ? (
                        <>
                          <Check className="h-3 w-3" /> Valid
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-3 w-3" /> Invalid JSON
                        </>
                      )}
                    </span>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="p-4 space-y-6">
                      <div>
                        <label className="text-sm font-medium mb-2 block">
                          Input Schema
                        </label>
                        <Textarea
                          value={inputSchemaJson}
                          onChange={(e) =>
                            handleInputSchemaChange(e.target.value)
                          }
                          className="font-mono text-sm min-h-[300px] resize-none"
                          placeholder="{}"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium mb-2 block">
                          Output Schema
                        </label>
                        <Textarea
                          value={outputSchemaJson}
                          onChange={(e) =>
                            handleOutputSchemaChange(e.target.value)
                          }
                          className="font-mono text-sm min-h-[200px] resize-none"
                          placeholder="{}"
                        />
                      </div>
                    </div>
                  </ScrollArea>
                </div>

                <div className="w-72 flex flex-col shrink-0">
                  <div className="px-4 py-2 border-b bg-muted/30 shrink-0">
                    <span className="text-sm font-medium">Preview</span>
                  </div>
                  <ScrollArea className="flex-1">
                    <div className="p-4 space-y-6">
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">
                          Tool
                        </label>
                        <p className="font-medium">{name}</p>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">
                          Source
                        </label>
                        <p className="text-sm">{tool.source}</p>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground block mb-1">
                          Version
                        </label>
                        <p className="text-sm">{tool.version || "1.0.0"}</p>
                      </div>
                      <hr />
                      <div>
                        <label className="text-xs text-muted-foreground block mb-2">
                          Summary
                        </label>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">
                              Input Fields:
                            </span>
                            <span className="font-medium">
                              {getFieldCount(inputSchema)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">
                              Output Fields:
                            </span>
                            <span className="font-medium">
                              {getFieldCount(outputSchema)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">
                              Required:
                            </span>
                            <span className="font-medium">
                              {getRequiredCount(inputSchema)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default ToolDetailDialog;
