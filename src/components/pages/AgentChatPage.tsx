'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Button, Input, Textarea, Select, Card, Badge } from '../ui';
import { RefreshCw, Plus, Eye, FilePlus, Upload, X, Edit, Trash2, Search, Bot, Circle, Loader2 } from 'lucide-react';

interface Session {
  session_id: string;
  created_at: string;
  context_summary?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
  metadata?: any;
}

interface ToolCall {
  tool: string;
  input?: any;
  output?: any;
  status: 'pending' | 'running' | 'completed' | 'error';
  error?: string;
}

interface ContextData {
  key: string;
  value: any;
}

interface FileData {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  description?: string;
  tags?: string[];
  uploaded_at: string;
  content: string;
  content_summary: string;
}

const AgentChatPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showContextForm, setShowContextForm] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDescription, setFileDescription] = useState('');
  const [fileTags, setFileTags] = useState('');
  const [sessionContext, setSessionContext] = useState<any>(null);
  const [showContextModal, setShowContextModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showAddContextModal, setShowAddContextModal] = useState(false);
  const [showEditFileModal, setShowEditFileModal] = useState(false);
  const [editingFile, setEditingFile] = useState<FileData | null>(null);
  const [contextKey, setContextKey] = useState('');
  const [contextValue, setContextValue] = useState('');
  const [contextValueType, setContextValueType] = useState<'string' | 'number' | 'boolean' | 'object'>('string');
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [streamingStatus, setStreamingStatus] = useState<string>('');
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [expandedToolSections, setExpandedToolSections] = useState<Set<number>>(new Set());
  const [contextDropdownOpen, setContextDropdownOpen] = useState(false);
  
  // Loading states
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isAddingContext, setIsAddingContext] = useState(false);
  const [isUpdatingFile, setIsUpdatingFile] = useState(false);
  const [isDeletingFile, setIsDeletingFile] = useState<string | null>(null);
  const [isDeletingContext, setIsDeletingContext] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const contextDropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextDropdownRef.current && !contextDropdownRef.current.contains(event.target as Node)) {
        setContextDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const API_BASE = 'http://localhost:5001/api';

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStreamingMessage]);

  // Load sessions on component mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Load messages and context when session changes
  useEffect(() => {
    if (selectedSession) {
      loadMessages();
      loadSessionContext();
    }
  }, [selectedSession]);

  const loadSessions = async () => {
    setIsLoadingSessions(true);
    try {
      const response = await fetch(`${API_BASE}/agent/sessions`);
      const data = await response.json();
      
      if (data.status === 'success') {
        // Convert session IDs to Session objects
        const sessionPromises = data.sessions.map(async (session: any) => {
          try {
            // Fetch context for each session to get summary
            // const contextResponse = await fetch(`${API_BASE}/agent/context?session_id=${session.session_id}`);
            // const contextData = await contextResponse.json();
            
            return {
              session_id: session.session_id,
              created_at: session.created_at, // We don't have creation time from API
              context_summary: 'No context'
            };
          } catch (error) {
            // If context fetch fails, still include the session
            return {
              session_id: session.session_id,
              created_at: session.created_at,
              context_summary: 'Error loading context'
            };
          }
        });
        
        const sessions = await Promise.all(sessionPromises);
        setSessions(sessions);
      } else {
        console.error('Error loading sessions:', data.message);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const loadMessages = async () => {
    try {
      const response = await fetch(`${API_BASE}/agent/chat?session_id=${selectedSession}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        // Convert API messages to our Message format
        const convertedMessages: Message[] = data.messages.map((msg: any) => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content,
          timestamp: msg.timestamp,
          tool_calls: msg.metadata?.tool_calls || [],
          metadata: msg.metadata
        }));
        
        setMessages(convertedMessages);
      } else {
        console.error('Error loading messages:', data.message);
        setMessages([]);
      }
    } catch (error) {
      console.error('Error loading messages:', error);
      setMessages([]);
    }
  };

  const loadSessionContext = async () => {
    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        // Keep the array format from vector database for proper file handling
        setSessionContext(data.context);
      } else {
        console.error('Error loading context:', data.message);
        setSessionContext(null);
      }
    } catch (error) {
      console.error('Error loading context:', error);
      setSessionContext(null);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedSession) return;

    const userMessage: Message = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setStreamingStatus('');
    setCurrentStreamingMessage('');
    setCurrentToolCalls([]);

    if (streamingEnabled) {
      await sendMessageStreaming(inputMessage);
    } else {
      await sendMessageNonStreaming(inputMessage);
    }
  };

  const sendMessageStreaming = async (message: string) => {
    try {
      const response = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: selectedSession,
          message: message,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let assistantMessage = '';
      let toolCalls: ToolCall[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        console.log('🔍 Received chunk:', chunk);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              // Debug logging
              console.log('🔍 Received streaming event:', data);
              
              switch (data.type) {
                case 'status':
                  console.log('🔍 Setting streaming status:', data.message);
                  setStreamingStatus(data.message);
                  break;
                case 'step_complete':
                  console.log('🔍 Step completed:', data.step);
                  setStreamingStatus(`${data.step} completed`);
                  break;
                case 'tool_call_start':
                  setStreamingStatus(`Calling tool: ${data.tool}`);
                  const newToolCall: ToolCall = {
                    tool: data.tool,
                    input: data.input,
                    status: 'running'
                  };
                  toolCalls = [...toolCalls, newToolCall];
                  setCurrentToolCalls(toolCalls);
                  break;
                case 'tool_call_complete':
                  setStreamingStatus(`Tool ${data.tool} completed`);
                  toolCalls = toolCalls.map(tc => 
                    tc.tool === data.tool 
                      ? { ...tc, status: 'completed', output: data.output }
                      : tc
                  );
                  setCurrentToolCalls(toolCalls);
                  break;
                case 'tool_call_error':
                  setStreamingStatus(`Tool ${data.tool} failed`);
                  toolCalls = toolCalls.map(tc => 
                    tc.tool === data.tool 
                      ? { ...tc, status: 'error', error: data.error }
                      : tc
                  );
                  setCurrentToolCalls(toolCalls);
                  break;
                case 'response_start':
                  setStreamingStatus('Generating response...');
                  break;
                case 'response_chunk':
                  assistantMessage += data.content;
                  setCurrentStreamingMessage(assistantMessage);
                  break;
                case 'response_complete':
                  setStreamingStatus('Response completed');
                  setCurrentStreamingMessage('');
                  const finalMessage: Message = {
                    role: 'assistant',
                    content: data.full_response,
                    timestamp: new Date().toISOString(),
                    tool_calls: toolCalls,
                    metadata: data.metadata
                  };
                  setMessages(prev => [...prev, finalMessage]);
                  setCurrentToolCalls([]);
                  break;
                case 'complete':
                  setStreamingStatus('');
                  setCurrentStreamingMessage('');
                  setCurrentToolCalls([]);
                  break;
                case 'error':
                  setStreamingStatus(`Error: ${data.message}`);
                  const errorMessage: Message = {
                    role: 'assistant',
                    content: `Error: ${data.message}`,
                    timestamp: new Date().toISOString()
                  };
                  setMessages(prev => [...prev, errorMessage]);
                  break;
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error in streaming:', error);
      setStreamingStatus(`Error: ${error}`);
      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: Failed to send message`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessageNonStreaming = async (message: string) => {
    try {
      const response = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: selectedSession,
          message: message,
          stream: false
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        // Reload messages to get the complete updated conversation
        await loadMessages();
      } else {
        const errorMessage: Message = {
          role: 'assistant',
          content: `Error: ${data.message}`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error: Failed to send message',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleToolSection = (messageIndex: number) => {
    const newExpanded = new Set(expandedToolSections);
    if (newExpanded.has(messageIndex)) {
      newExpanded.delete(messageIndex);
    } else {
      newExpanded.add(messageIndex);
    }
    setExpandedToolSections(newExpanded);
  };

  const getToolStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'pending': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getToolStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '🔄';
      case 'error': return '❌';
      case 'pending': return '⏳';
      default: return '⏳';
    }
  };


  const uploadFile = async () => {
    if (!selectedFile || !selectedSession) return;

    setIsUploadingFile(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('description', fileDescription);
    formData.append('tags', fileTags);

    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert('File uploaded successfully!');
        setSelectedFile(null);
        setFileDescription('');
        setFileTags('');
        setShowUploadModal(false);
        // Reload context to show updated content
        loadSessionContext();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      alert('Error: Failed to upload file');
    } finally {
      setIsUploadingFile(false);
    }
  };

  const updateFile = async () => {
    if (!editingFile || !selectedSession) return;

    setIsUpdatingFile(true);
    const formData = new FormData();
    if (selectedFile) {
      formData.append('file', selectedFile);
    }
    formData.append('file_id', editingFile.file_id);
    formData.append('description', fileDescription);
    formData.append('tags', fileTags);

    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}`, {
        method: 'PUT',
        body: formData
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert('File updated successfully!');
        setEditingFile(null);
        setSelectedFile(null);
        setFileDescription('');
        setFileTags('');
        setShowEditFileModal(false);
        // Reload context to show updated content
        loadSessionContext();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      alert('Error: Failed to update file');
    } finally {
      setIsUpdatingFile(false);
    }
  };

  const deleteFile = async (fileId: string) => {
    if (!selectedSession) return;

    if (!confirm('Are you sure you want to delete this file?')) return;

    setIsDeletingFile(fileId);
    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}&file_id=${fileId}`, {
        method: 'DELETE'
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert('File deleted successfully!');
        // Reload context to show updated content
        loadSessionContext();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      alert('Error: Failed to delete file');
    } finally {
      setIsDeletingFile(null);
    }
  };

  const addContext = async () => {
    if (!contextKey.trim() || !contextValue.trim() || !selectedSession) return;

    setIsAddingContext(true);
    let parsedValue: any = contextValue;
    
    // Parse value based on type
    switch (contextValueType) {
      case 'number':
        parsedValue = parseFloat(contextValue);
        if (isNaN(parsedValue)) {
          alert('Invalid number format');
          setIsAddingContext(false);
          return;
        }
        break;
      case 'boolean':
        parsedValue = contextValue.toLowerCase() === 'true';
        break;
      case 'object':
        try {
          parsedValue = JSON.parse(contextValue);
        } catch (error) {
          alert('Invalid JSON format');
          setIsAddingContext(false);
          return;
        }
        break;
      default:
        parsedValue = contextValue;
    }

    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          key: contextKey,
          value: parsedValue
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert('Context added successfully!');
        setContextKey('');
        setContextValue('');
        setContextValueType('string');
        setShowAddContextModal(false);
        // Reload context to show updated content
        loadSessionContext();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      alert('Error: Failed to add context');
    } finally {
      setIsAddingContext(false);
    }
  };

  const deleteContext = async (key: string) => {
    if (!selectedSession) return;

    if (!confirm(`Are you sure you want to delete the context key "${key}"?`)) return;

    setIsDeletingContext(key);
    try {
      const response = await fetch(`${API_BASE}/agent/context?session_id=${selectedSession}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          key: key
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert('Context deleted successfully!');
        // Reload context to show updated content
        loadSessionContext();
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      alert('Error: Failed to delete context');
    } finally {
      setIsDeletingContext(null);
    }
  };

  const editFile = (file: FileData) => {
    setEditingFile(file);
    setFileDescription(file.description || '');
    setFileTags(file.tags?.join(', ') || '');
    setSelectedFile(null);
    setShowEditFileModal(true);
  };

  const createNewSession = async () => {
    setIsCreatingSession(true);
    try {
      const response = await fetch(`${API_BASE}/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: 'Hey!'
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        const newSession: Session = {
          session_id: data.session_id,
          created_at: new Date().toISOString(),
          context_summary: 'New session'
        };
        setSessions(prev => [...prev, newSession]);
        setSelectedSession(data.session_id);
      }
    } catch (error) {
      alert('Error: Failed to create new session');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputMessage(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Check file size (2MB = 2 * 1024 * 1024 bytes)
      const maxSize = 2 * 1024 * 1024; // 2MB in bytes
      if (file.size > maxSize) {
        alert('File size must be less than 2MB. Please select a smaller file.');
        // Reset the input
        e.target.value = '';
        return;
      }
      setSelectedFile(file);
    }
  };

  const getFilesFromContext = (): FileData[] => {
    if (!sessionContext) return [];
    
    // Handle array format from vector database
    if (Array.isArray(sessionContext)) {
      // Group chunks by original_key to reconstruct files
      const fileChunks: { [key: string]: any[] } = {};
      
      sessionContext.forEach((item: any) => {
        if (item.metadata?.type === 'file_chunk') {
          const originalKey = item.metadata.original_key;
          if (!fileChunks[originalKey]) {
            fileChunks[originalKey] = [];
          }
          fileChunks[originalKey].push(item);
        }
      });
      
      // Reconstruct files from chunks
      const files: FileData[] = [];
      Object.entries(fileChunks).forEach(([originalKey, chunks]) => {
        // Sort chunks by chunk_index
        chunks.sort((a, b) => a.metadata.chunk_index - b.metadata.chunk_index);
        
        // Reconstruct full content
        const fullContent = chunks.map(chunk => chunk.content).join('');
        
        // Use metadata from first chunk
        const firstChunk = chunks[0];
        const fileData: FileData = {
          file_id: originalKey.replace('file_', ''),
          filename: firstChunk.metadata.filename,
          file_type: firstChunk.metadata.file_type,
          file_size: fullContent.length,
          description: firstChunk.metadata.description || '',
          tags: firstChunk.metadata.tags || [],
          uploaded_at: firstChunk.metadata.timestamp,
          content: fullContent,
          content_summary: firstChunk.metadata.content_summary || ''
        };
        
        files.push(fileData);
      });
      
      return files;
    }
    
    // Handle object format (legacy)
    if (sessionContext.files) {
      return sessionContext.files;
    }
    
    return [];
  };

  const getContextKeys = (): string[] => {
    if (!sessionContext) return [];
    
    // Handle array format (from vector DB)
    if (Array.isArray(sessionContext)) {
      // Check if this is the new format where items have content and empty metadata
      const hasContentItems = sessionContext.some((item: any) => 
        item.content && typeof item.content === 'string' && 
        (!item.metadata || Object.keys(item.metadata).length === 0)
      );
      
      if (hasContentItems) {
        // This is the new format - generate meaningful keys from content
        const keys = sessionContext.map((item: any, index: number) => {
          const content = item.content;
          // Create a meaningful key from the content
          if (content.length <= 30) {
            return content;
          } else {
            // Truncate and add ellipsis for longer content
            return content.substring(0, 30) + '...';
          }
        });
        return keys;
      }
      
      // Get unique original_keys for non-file items (old format)
      const keys = new Set<string>();
      sessionContext.forEach((item: any) => {
        if (item.metadata?.type === 'text' && item.metadata?.original_key) {
          keys.add(item.metadata.original_key);
        }
      });
      
      return Array.from(keys);
    }
    
    // Object format - filter out files
    return Object.keys(sessionContext).filter(key => key !== 'files' && !key.startsWith('file_'));
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="flex h-screen">
        {/* Left Sidebar - Chat History */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h1 className="text-lg font-semibold">Chat History</h1>
              <div className="flex items-center space-x-2">
                <button 
                  onClick={loadSessions}
                  className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center"
                >
                  <RefreshCw size={16} className="text-gray-600" />
                </button>
              </div>
            </div>
          </div>
          
          {/* Search Bar */}
          <div className="p-4 border-b border-gray-200">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search conversations..."
                className="w-full pl-10 pr-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          
          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {isLoadingSessions ? (
              <div className="text-center py-4 text-gray-500">
                Loading sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-4 text-gray-500">
                No sessions found
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedSession === session.session_id
                      ? 'bg-blue-50 border border-blue-200'
                      : 'bg-gray-50 hover:bg-gray-100 border border-gray-200'
                  }`}
                  onClick={() => setSelectedSession(session.session_id)}
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-4 h-4 rounded-sm ${
                      selectedSession === session.session_id ? 'bg-blue-600' : 'bg-gray-400'
                    }`}></div>
                    <div className="flex-1">
                      <div className="font-medium truncate text-gray-900">
                        {session.session_id.slice(0, 8)}...
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(session.created_at).toLocaleDateString()}
                      </div>
                      {session.context_summary && (
                        <div className="text-xs text-gray-600 truncate">
                          {session.context_summary}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {/* New Conversation Button */}
          <div className="p-4 border-t border-gray-200">
            <button 
              onClick={createNewSession}
              disabled={isCreatingSession}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white py-3 px-4 rounded-lg flex items-center justify-center space-x-2 font-medium"
            >
              {isCreatingSession ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Plus size={18} />
              )}
              <span>{isCreatingSession ? 'Creating...' : 'New Conversation'}</span>
            </button>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col bg-gray-50">
          {/* Chat Header */}
          <div className="p-4 border-b border-gray-200 bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <Circle size={12} className="text-green-500 fill-current" />
                  <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                    <Bot size={14} className="text-white" />
                  </div>
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Agent Chat</h2>
                  <p className="text-sm text-gray-500">AI Assistant</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                {selectedSession && (
                  <div className="relative" ref={contextDropdownRef}>
                    <button 
                      onClick={() => setContextDropdownOpen(!contextDropdownOpen)}
                      className="flex items-center space-x-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg"
                    >
                      <span className="text-gray-700">Context</span>
                      <span className={`text-gray-500 transition-transform ${contextDropdownOpen ? 'rotate-180' : ''}`}>▼</span>
                    </button>
                    
                    {/* Context Dropdown Menu */}
                    {contextDropdownOpen && (
                      <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                        <div className="py-1">
                          <button
                            onClick={() => {
                              setShowContextModal(true);
                              setContextDropdownOpen(false);
                            }}
                            className="flex items-center space-x-2 w-full px-4 py-2 text-left hover:bg-gray-50"
                          >
                            <Eye size={16} className="text-gray-600" />
                            <span>View Context</span>
                          </button>
                          <button
                            onClick={() => {
                              setShowAddContextModal(true);
                              setContextDropdownOpen(false);
                            }}
                            className="flex items-center space-x-2 w-full px-4 py-2 text-left hover:bg-gray-50"
                          >
                            <FilePlus size={16} className="text-gray-600" />
                            <span>Add Context</span>
                          </button>
                          <button
                            onClick={() => {
                              setShowUploadModal(true);
                              setContextDropdownOpen(false);
                            }}
                            className="flex items-center space-x-2 w-full px-4 py-2 text-left hover:bg-gray-50"
                          >
                            <Upload size={16} className="text-gray-600" />
                            <span>Add File</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            
            {/* Streaming Controls */}
            {selectedSession && (
              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="streaming-toggle"
                    checked={streamingEnabled}
                    onChange={(e) => setStreamingEnabled(e.target.checked)}
                    className="rounded border-gray-300 bg-white"
                  />
                  <label htmlFor="streaming-toggle" className="text-sm font-medium text-gray-700">
                    Enable Streaming
                  </label>
                </div>

              </div>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-900 border border-gray-200'
                  }`}
                >
                  <div className="text-sm">{message.content}</div>
                  
                  {/* Tool Calls Section */}
                  {message.role === 'assistant' && message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1">
                            <span className="text-xs font-medium text-gray-600">
                              {message.tool_calls.length} tool{message.tool_calls.length > 1 ? 's' : ''} used
                            </span>
                            <div className="flex items-center gap-1">
                              {message.tool_calls.map((toolCall, toolIndex) => (
                                <span key={toolIndex} className={`w-2 h-2 rounded-full ${getToolStatusColor(toolCall.status).replace('text-', 'bg-').replace('bg-gray-100', 'bg-gray-300')}`}></span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => toggleToolSection(index)}
                          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          {expandedToolSections.has(index) ? (
                            <>
                              <span>Hide</span>
                              <span className="text-xs">▲</span>
                            </>
                          ) : (
                            <>
                              <span>Show</span>
                              <span className="text-xs">▼</span>
                            </>
                          )}
                        </button>
                      </div>
                      
                      {expandedToolSections.has(index) && (
                        <div className="mt-3 space-y-3">
                          {message.tool_calls.map((toolCall, toolIndex) => (
                            <div key={toolIndex} className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                              {/* Tool Header */}
                              <div className="flex items-center justify-between px-3 py-2 bg-gray-100 border-b border-gray-200">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-700">{toolCall.tool}</span>
                                  <span className={`text-xs px-2 py-1 rounded-full ${getToolStatusColor(toolCall.status)}`}>
                                    {getToolStatusIcon(toolCall.status)} {toolCall.status}
                                  </span>
                                </div>
                              </div>
                              
                              {/* Tool Content */}
                              <div className="p-3 space-y-3">
                                {toolCall.input && (
                                  <div>
                                    <div className="text-xs font-medium text-gray-600 mb-1">Input</div>
                                    <div className="bg-white rounded border border-gray-200 p-2 text-xs text-gray-700 font-mono overflow-x-auto">
                                      {typeof toolCall.input === 'object' ? JSON.stringify(toolCall.input, null, 2) : String(toolCall.input)}
                                    </div>
                                  </div>
                                )}
                                
                                {toolCall.output && (
                                  <div>
                                    <div className="text-xs font-medium text-gray-600 mb-1">Output</div>
                                    <div className="bg-white rounded border border-gray-200 p-2 text-xs text-gray-700 font-mono overflow-x-auto max-h-32 overflow-y-auto">
                                      {typeof toolCall.output === 'object' ? JSON.stringify(toolCall.output, null, 2) : String(toolCall.output)}
                                    </div>
                                  </div>
                                )}
                                
                                {toolCall.error && (
                                  <div>
                                    <div className="text-xs font-medium text-red-600 mb-1">Error</div>
                                    <div className="bg-red-50 rounded border border-red-200 p-2 text-xs text-red-700 font-mono">
                                      {toolCall.error}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            
            {isLoading && !streamingEnabled && (
              <div className="flex justify-start">
                <div className="bg-white text-gray-900 px-4 py-2 rounded-lg border border-gray-200">
                  <div className="text-sm">Thinking...</div>
                </div>
              </div>
            )}
            
            {/* Streaming Message */}
            {currentStreamingMessage && (
              <div className="flex justify-start">
                <div className="bg-white text-gray-900 px-4 py-2 rounded-lg border border-gray-200">
                  <div className="text-sm">{currentStreamingMessage}</div>
                  
                  {/* Current Tool Calls */}
                  {currentToolCalls.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-xs font-medium text-gray-600">
                          {currentToolCalls.length} active tool{currentToolCalls.length > 1 ? 's' : ''}
                        </span>
                        <div className="flex items-center gap-1">
                          {currentToolCalls.map((toolCall, toolIndex) => (
                            <span key={toolIndex} className={`w-2 h-2 rounded-full ${getToolStatusColor(toolCall.status).replace('text-', 'bg-').replace('bg-gray-100', 'bg-gray-300')}`}></span>
                          ))}
                        </div>
                      </div>
                      <div className="space-y-3">
                        {currentToolCalls.map((toolCall, toolIndex) => (
                          <div key={toolIndex} className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                            {/* Tool Header */}
                            <div className="flex items-center justify-between px-3 py-2 bg-gray-100 border-b border-gray-200">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-700">{toolCall.tool}</span>
                                <span className={`text-xs px-2 py-1 rounded-full ${getToolStatusColor(toolCall.status)}`}>
                                  {getToolStatusIcon(toolCall.status)} {toolCall.status}
                                </span>
                              </div>
                            </div>
                            
                            {/* Tool Content */}
                            <div className="p-3 space-y-3">
                              {toolCall.input && (
                                <div>
                                  <div className="text-xs font-medium text-gray-600 mb-1">Input</div>
                                  <div className="bg-white rounded border border-gray-200 p-2 text-xs text-gray-700 font-mono overflow-x-auto">
                                    {typeof toolCall.input === 'object' ? JSON.stringify(toolCall.input, null, 2) : String(toolCall.input)}
                                  </div>
                                </div>
                              )}
                              
                              {toolCall.output && (
                                <div>
                                  <div className="text-xs font-medium text-gray-600 mb-1">Output</div>
                                  <div className="bg-white rounded border border-gray-200 p-2 text-xs text-gray-700 font-mono overflow-x-auto max-h-32 overflow-y-auto">
                                    {typeof toolCall.output === 'object' ? JSON.stringify(toolCall.output, null, 2) : String(toolCall.output)}
                                  </div>
                                </div>
                              )}
                              
                              {toolCall.error && (
                                <div>
                                  <div className="text-xs font-medium text-red-600 mb-1">Error</div>
                                  <div className="bg-red-50 rounded border border-red-200 p-2 text-xs text-red-700 font-mono">
                                    {toolCall.error}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date().toLocaleTimeString()}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-6 border-t border-gray-200 bg-white">
            <div className="relative">
              <div className="flex items-end gap-3 bg-gray-50 rounded-2xl border-2 border-gray-200 focus-within:border-blue-500 focus-within:bg-white transition-all duration-200 p-4">
                <div className="flex-1 min-h-[44px] max-h-32 overflow-y-auto">
                  <textarea
                    placeholder={selectedSession ? "Type your message..." : "Select a session to start chatting"}
                    value={inputMessage}
                    onChange={handleTextareaChange}
                    onKeyDown={handleKeyDown}
                    className="w-full bg-transparent border-none outline-none resize-none text-gray-900 placeholder-gray-500 text-sm leading-relaxed"
                    rows={1}
                    disabled={!selectedSession}
                    style={{ minHeight: '44px', maxHeight: '128px' }}
                  />
                </div>
                <button
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || !selectedSession || isLoading}
                  className="flex-shrink-0 w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95 shadow-sm hover:shadow-md"
                >
                  {isLoading ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </button>
              </div>
              
              {/* Character count and status */}
              <div className="flex items-center justify-between mt-2 px-1">
                <div className="text-xs text-gray-400">
                  {inputMessage.length > 0 && `${inputMessage.length} characters`}
                </div>
                {streamingStatus && (
                  <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                    {streamingStatus}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Context View Modal */}
      {showContextModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Session Context</h2>
              <Button
                onClick={() => setShowContextModal(false)}
                variant="ghost"
                size="sm"
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={16} />
              </Button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {sessionContext ? (
                <div className="space-y-6">
                  {/* Files Section */}
                  {getFilesFromContext().length > 0 && (
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">
                        Files ({getFilesFromContext().length})
                      </h3>
                      <div className="space-y-4">
                        {getFilesFromContext().map((file: FileData, index: number) => (
                          <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="font-medium text-gray-900">{file.filename}</div>
                                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                    {file.file_type}
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    {(file.file_size / 1024).toFixed(1)} KB
                                  </span>
                                </div>
                                
                                {file.description && (
                                  <div className="text-sm text-gray-600 mb-2">{file.description}</div>
                                )}
                                
                                {file.tags && file.tags.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mb-3">
                                    {file.tags.map((tag: string, tagIndex: number) => (
                                      <span key={tagIndex} className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                        {tag}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                
                                <div className="text-xs text-gray-500">
                                  Uploaded: {new Date(file.uploaded_at).toLocaleString()}
                                </div>
                              </div>
                              <div className="flex gap-2 ml-4">
                                <Button
                                  onClick={() => editFile(file)}
                                  variant="outline"
                                  size="sm"
                                  disabled={isUpdatingFile}
                                  className="text-gray-700 border-gray-300 hover:bg-gray-50 disabled:opacity-50"
                                >
                                  <Edit size={14} className="mr-1" />
                                  Edit
                                </Button>
                                <Button
                                  onClick={() => deleteFile(file.file_id)}
                                  variant="outline"
                                  size="sm"
                                  disabled={isDeletingFile === file.file_id}
                                  className="text-red-600 border-red-300 hover:bg-red-50 disabled:opacity-50"
                                >
                                  {isDeletingFile === file.file_id ? (
                                    <>
                                      <Loader2 size={14} className="animate-spin mr-1" />
                                      Deleting...
                                    </>
                                  ) : (
                                    <>
                                      <Trash2 size={14} className="mr-1" />
                                      Delete
                                    </>
                                  )}
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Other Context Section */}
                  {getContextKeys().length > 0 && (
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Other Context</h3>
                      <div className="space-y-3">
                        {getContextKeys().map((key) => {
                          let value: any;
                          let metadata: any = {};
                          
                          // Handle array format from vector database
                          if (Array.isArray(sessionContext)) {
                            // Check if this is the new format (content items with empty metadata)
                            const hasContentItems = sessionContext.some((item: any) => 
                              item.content && typeof item.content === 'string' && 
                              (!item.metadata || Object.keys(item.metadata).length === 0)
                            );
                            
                            if (hasContentItems) {
                              // New format - find the item that matches this key
                              const item = sessionContext.find((item: any) => {
                                const content = item.content;
                                const itemKey = content.length <= 30 ? content : content.substring(0, 30) + '...';
                                return itemKey === key;
                              });
                              if (item) {
                                value = item.content;
                                metadata = item.metadata || {};
                              }
                            } else {
                              // Old format - look for original_key in metadata
                              const item = sessionContext.find((item: any) => 
                                item.metadata?.original_key === key
                              );
                              if (item) {
                                value = item.content;
                                metadata = item.metadata || {};
                              }
                            }
                          } else {
                            // Object format (legacy)
                            value = sessionContext[key];
                          }
                          
                          return (
                            <div key={key} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-gray-900 mb-2">{key}</div>
                                  <div className="text-sm text-gray-600 bg-white p-3 rounded border border-gray-200">
                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                  </div>
                                  {metadata.timestamp && (
                                    <div className="text-xs text-gray-500 mt-2">
                                      Added: {new Date(metadata.timestamp).toLocaleString()}
                                    </div>
                                  )}
                                </div>
                                <div className="ml-4">
                                  <Button
                                    onClick={() => deleteContext(key)}
                                    variant="outline"
                                    size="sm"
                                    disabled={isDeletingContext === key}
                                    className="text-red-600 border-red-300 hover:bg-red-50 disabled:opacity-50"
                                  >
                                    {isDeletingContext === key ? (
                                      <>
                                        <Loader2 size={14} className="animate-spin mr-1" />
                                        Deleting...
                                      </>
                                    ) : (
                                      <>
                                        <Trash2 size={14} className="mr-1" />
                                        Delete
                                      </>
                                    )}
                                  </Button>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {getFilesFromContext().length === 0 && getContextKeys().length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      <div className="text-lg font-medium mb-2">No context available</div>
                      <div className="text-sm">Upload files or add context to get started.</div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-lg font-medium mb-2">Loading context...</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Context Modal */}
      {showAddContextModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Add Context</h2>
              <Button
                onClick={() => {
                  setShowAddContextModal(false);
                  setContextKey('');
                  setContextValue('');
                  setContextValueType('string');
                }}
                variant="ghost"
                size="sm"
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={16} />
              </Button>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                {/* Context Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Context Key
                  </label>
                  <Input
                    placeholder="Enter context key"
                    value={contextKey}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setContextKey(e.target.value)}
                    className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                  />
                </div>
                {/* Value Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Value Type
                  </label>
                  <Select
                    value={contextValueType}
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setContextValueType(e.target.value as any)}
                    className="bg-white border-gray-300 text-gray-900"
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                    <option value="boolean">Boolean</option>
                    <option value="object">JSON Object</option>
                  </Select>
                </div>
                {/* Context Value */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Context Value
                  </label>
                  {contextValueType === 'object' ? (
                    <Textarea
                      placeholder='{"key": "value"}'
                      value={contextValue}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContextValue(e.target.value)}
                      rows={4}
                      className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                    />
                  ) : (
                    <Input
                      placeholder={`Enter ${contextValueType} value`}
                      value={contextValue}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setContextValue(e.target.value)}
                      className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                    />
                  )}
                </div>
                {/* Buttons */}
                <div className="flex justify-end gap-3">
                  <Button
                    onClick={() => {
                      setShowAddContextModal(false);
                      setContextKey('');
                      setContextValue('');
                      setContextValueType('string');
                    }}
                    variant="outline"
                    size="sm"
                    className="text-gray-700 border-gray-300 hover:bg-gray-50"
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={addContext}
                    size="sm" 
                    disabled={!contextKey.trim() || !contextValue.trim() || isAddingContext}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white"
                  >
                    {isAddingContext ? (
                      <>
                        <Loader2 size={14} className="animate-spin mr-1" />
                        Adding...
                      </>
                    ) : (
                      'Add Context'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload File Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Upload File</h2>
              <Button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setFileDescription('');
                  setFileTags('');
                }}
                variant="ghost"
                size="sm"
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={16} />
              </Button>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    File
                  </label>
                  <Input
                    type="file"
                    onChange={handleFileSelect}
                    className="bg-white border-gray-300 text-gray-900"
                  />
                  <div className="mt-1 text-xs text-gray-500">
                    Maximum file size: 2MB
                  </div>
                  {selectedFile && (
                    <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                      <div className="font-medium">Selected file: {selectedFile.name}</div>
                      <div>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <Input
                    placeholder="Enter file description"
                    value={fileDescription}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFileDescription(e.target.value)}
                    className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tags (comma separated)
                  </label>
                  <Input
                    placeholder="e.g. requirements, python"
                    value={fileTags}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFileTags(e.target.value)}
                    className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button
                    onClick={() => {
                      setShowUploadModal(false);
                      setSelectedFile(null);
                      setFileDescription('');
                      setFileTags('');
                    }}
                    variant="outline"
                    size="sm"
                    className="text-gray-700 border-gray-300 hover:bg-gray-50"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={uploadFile}
                    size="sm"
                    disabled={!selectedFile || isUploadingFile}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white"
                  >
                    {isUploadingFile ? (
                      <>
                        <Loader2 size={14} className="animate-spin mr-1" />
                        Uploading...
                      </>
                    ) : (
                      'Upload'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit File Modal */}
      {showEditFileModal && editingFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Edit File</h2>
              <Button
                onClick={() => {
                  setShowEditFileModal(false);
                  setEditingFile(null);
                  setSelectedFile(null);
                  setFileDescription('');
                  setFileTags('');
                }}
                variant="ghost"
                size="sm"
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={16} />
              </Button>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Replace File (optional)
                  </label>
                  <Input
                    type="file"
                    onChange={handleFileSelect}
                    className="bg-white border-gray-300 text-gray-900"
                  />
                  <div className="mt-1 text-xs text-gray-500">
                    Maximum file size: 2MB
                  </div>
                  {selectedFile && (
                    <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700">
                      <div className="font-medium">Selected file: {selectedFile.name}</div>
                      <div>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</div>
                    </div>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <Input
                    placeholder="Enter file description"
                    value={fileDescription}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFileDescription(e.target.value)}
                    className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tags (comma separated)
                  </label>
                  <Input
                    placeholder="e.g. requirements, python"
                    value={fileTags}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFileTags(e.target.value)}
                    className="bg-white border-gray-300 text-gray-900 placeholder-gray-500"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button
                    onClick={() => {
                      setShowEditFileModal(false);
                      setEditingFile(null);
                      setSelectedFile(null);
                      setFileDescription('');
                      setFileTags('');
                    }}
                    variant="outline"
                    size="sm"
                    className="text-gray-700 border-gray-300 hover:bg-gray-50"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={updateFile}
                    size="sm"
                    disabled={isUpdatingFile}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white"
                  >
                    {isUpdatingFile ? (
                      <>
                        <Loader2 size={14} className="animate-spin mr-1" />
                        Saving...
                      </>
                    ) : (
                      'Save Changes'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentChatPage; 