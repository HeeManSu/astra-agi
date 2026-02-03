import { useState, useEffect } from "react";
import { useAppSelector } from "@/store/hooks";
import { updateTool } from "@/api/tools";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Wrench, Save, FileJson, Check, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function ToolDetailDialog({ tool, open, onOpenChange, onSave }) {
  const { serverUrl, apiKey } = useAppSelector((state) => state.app);

  const [activeTab, setActiveTab] = useState("definition");
  const [saving, setSaving] = useState(false);
  const [jsonValid, setJsonValid] = useState(true);

  // Editable state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [inputSchemaJson, setInputSchemaJson] = useState("");
  const [outputSchemaJson, setOutputSchemaJson] = useState("");

  // Reset form when tool changes
  useEffect(() => {
    if (tool) {
      setName(tool.name || "");
      setDescription(tool.description || "");
      setInputSchemaJson(JSON.stringify(tool.input_schema || {}, null, 2));
      setOutputSchemaJson(JSON.stringify(tool.output_schema || {}, null, 2));
      setActiveTab("definition");
      setJsonValid(true);
    }
  }, [tool]);

  // Validate JSON
  const validateJson = (json) => {
    if (!json || json.trim() === "") return true;
    try {
      JSON.parse(json);
      return true;
    } catch {
      return false;
    }
  };

  // Handle input schema change
  const handleInputSchemaChange = (value) => {
    setInputSchemaJson(value);
    setJsonValid(validateJson(value) && validateJson(outputSchemaJson));
  };

  // Handle output schema change
  const handleOutputSchemaChange = (value) => {
    setOutputSchemaJson(value);
    setJsonValid(validateJson(inputSchemaJson) && validateJson(value));
  };

  // Save changes
  const handleSave = async () => {
    if (!jsonValid) {
      toast.error("Please fix JSON syntax errors before saving");
      return;
    }

    setSaving(true);
    try {
      const data = {
        name,
        description,
        input_schema: inputSchemaJson ? JSON.parse(inputSchemaJson) : null,
        output_schema: outputSchemaJson ? JSON.parse(outputSchemaJson) : null,
      };

      await updateTool(serverUrl, apiKey, tool.slug, data);
      toast.success("Tool updated successfully");
      onSave?.();
    } catch (error) {
      console.error("Failed to update tool:", error);
      toast.error("Failed to update tool");
    } finally {
      setSaving(false);
    }
  };

  // Get field summary
  const getFieldCount = (schema) => {
    if (!schema?.properties) return 0;
    return Object.keys(schema.properties).length;
  };

  const inputSchema = (() => {
    try {
      return JSON.parse(inputSchemaJson);
    } catch {
      return {};
    }
  })();

  const outputSchema = (() => {
    try {
      return JSON.parse(outputSchemaJson);
    } catch {
      return {};
    }
  })();

  if (!tool) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] w-[95vw] h-[90vh] p-0 gap-0 flex flex-col">
        {/* Header */}
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
          <div className="flex items-center gap-2">
            <Button onClick={handleSave} disabled={saving || !jsonValid}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Body with Sidebar */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar */}
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
              {/* Builder tab - coming soon */}
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

          {/* Main Content */}
          <div className="flex-1 flex overflow-hidden">
            {activeTab === "definition" && (
              <div className="flex-1 flex">
                {/* JSON Editor Panel */}
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

                {/* Preview Panel */}
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
                              {inputSchema?.required?.length || 0}
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
