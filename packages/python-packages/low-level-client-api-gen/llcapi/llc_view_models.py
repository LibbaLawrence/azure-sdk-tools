# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Any, Dict
from ._token import Token
from ._token_kind import TokenKind
from autorest.codegen.models import RequestBuilder, CodeModel, request_builder,build_schema, Operation

JSON_FIELDS = ["Name", "Version", "VersionString", "Navigation", "Tokens", "Diagnostics", "PackageName"]
PARAM_FIELDS = ["name", "type", "default", "optional", "indent"]
OP_FIELDS = ["operation", "parameters", "indent"]

class FormattingClass:
    def add_whitespace(self,indent):
        if indent:
            self.add_token(Token(" " * (indent * 4)))

    def add_space(self):
        self.add_token(Token(" ", TokenKind.Whitespace))

    def add_new_line(self,additional_line_count=0):
        self.add_token(Token("", TokenKind.Newline))
        for n in range(additional_line_count):
            self.add_space()
            self.add_token(Token("", TokenKind.Newline))

    def add_punctuation(self, value, prefix_space=False, postfix_space=False):
        if prefix_space:
            self.add_space()
        self.add_token(Token(value, TokenKind.Punctuation))
        if postfix_space:
            self.add_space()

    def add_line_marker(self, text):
        token = Token("", TokenKind.LineIdMarker)
        token.set_definition_id(text)
        self.add_token(token)

    def add_text(self, id, text, nav):
        token = Token(text, TokenKind.Text)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)
    
    def add_comment(self,id,text,nav):
        token = Token(text, TokenKind.Comment)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)

    def add_typename(self, id, text, nav):
        token = Token(text, TokenKind.TypeName)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)
    
    def add_stringliteral(self, id, text,nav):
        token = Token(text, TokenKind.StringLiteral)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)

    def add_literal(self, id, text):
        token = Token(text, TokenKind.Literal)
        token.DefinitionId = id
        self.add_token(token)

    def add_keyword(self, id, keyword, nav):
        token = Token(keyword, TokenKind.Keyword)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)
     
    def add_navigation(self, navigation):
        self.Navigation.append(navigation)

class LLCClientView(FormattingClass):
    """Entity class that holds LLC view for all namespaces within a package"""
    def __init__(self, operation_groups, pkg_name="", endpoint="endpoint",endpoint_type="string",credential="Credential",credential_type="AzureCredential"):
        self.Name = pkg_name
        self.Language = "LLC"
        self.Tokens = []
        self.Operations = []
        self.Operation_Groups= operation_groups
        self.Navigation = []
        self.Diagnostics = []
        self.endpoint_type = endpoint_type
        self.endpoint = endpoint
        self.credential = credential 
        self.credential_type = credential_type
        self.namespace = "Azure."+pkg_name

    @classmethod
    def from_yaml(cls,yaml_data: Dict[str,Any]):
        operation_groups = []
        #Iterate through Operations in OperationGroups
        for op_groups in range(0,len(yaml_data["operationGroups"])):
            operation_group_view = LLCOperationGroupView.from_yaml(yaml_data, op_groups,"Azure."+yaml_data["info"]["title"])
            operation_group = LLCOperationGroupView(operation_group_view.operation_group,operation_group_view.operations,"Azure."+yaml_data["info"]["title"])
            operation_groups.append(operation_group)

        return cls(
            operation_groups =operation_groups,
            pkg_name = yaml_data["info"]["title"],
            endpoint = yaml_data["globalParameters"][0]["language"]["default"]["name"],
            endpoint_type = yaml_data["globalParameters"][0]["schema"]["type"] ,
        )

    def add_token(self, token):
        self.Tokens.append(token)

    def add_operation_group(self,operation_group):
        self.Operation_Groups.append(operation_group)
    
    def to_token(self): 
    #Create view 
        #Namespace
        self.add_keyword(self.namespace,self.namespace,self.namespace)
        self.add_space()
        self.add_punctuation("{")
        self.add_new_line(1)

        #Name of client
        self.add_whitespace(1)
        self.add_keyword(self.namespace+self.Name,self.Name,self.namespace+self.Name)
        self.add_punctuation("(")
        self.add_stringliteral(None,self.endpoint_type,None)
        self.add_space()
        self.add_text(None,self.endpoint, None)

        self.add_punctuation(",")
        self.add_space()
        self.add_stringliteral(None,self.credential_type,None)
        self.add_space()
        self.add_text(None,self.credential,None)
 
        self.add_punctuation(")")
        self.add_new_line(1)

        #Create Overview
        for operation_group in self.Operation_Groups:
            operation_group.to_token()
            operation_tokens = operation_group.overview_tokens
            for token in operation_tokens:
                    if token:
                        self.add_token(token)
            self.add_new_line(1)

        navigation = self.to_child_tokens()

        self.add_new_line()

        self.add_punctuation("}")

        self.add_navigation(navigation)

        return self.Tokens 

    def to_child_tokens(self):
        #Set Navigation
        navigation = Navigation(self.namespace, None)
        navigation.set_tag(NavigationTag(Kind.type_package))
        self.add_new_line(1)
        for operation_group_view in self.Operation_Groups:
            #Add children
            child_nav = Navigation(operation_group_view.operation_group, self.namespace + operation_group_view.operation_group)
            child_nav.set_tag(NavigationTag(Kind.type_class))
            navigation.add_child(child_nav)
            op_group = operation_group_view.get_tokens()
            for token in op_group:
                self.add_token(token)
            #Set up operations and add to token
            
            for operation_view in operation_group_view.operations:
                #Add operation comments
                child_nav1 = Navigation(operation_view.operation, self.namespace + operation_view.operation)
                child_nav1.set_tag(NavigationTag(Kind.type_method))
                child_nav.add_child(child_nav1)

        return navigation 

    def to_json(self):
        obj_dict={}
        self.to_token()
        for key in JSON_FIELDS:
            if key in self.__dict__:
                obj_dict[key] = self.__dict__[key]
        for i in range(0,len(obj_dict["Tokens"])):
            #Break down token objects into dictionary
            if obj_dict["Tokens"][i]:
                obj_dict["Tokens"][i] = {"Kind": obj_dict["Tokens"][i].Kind.value, "Value" : obj_dict["Tokens"][i].Value, 
                    "NavigateToId": obj_dict["Tokens"][i].NavigateToId, "DefinitionId": obj_dict["Tokens"][i].DefinitionId}

            #Remove Null Values from Tokens
            obj_dict["Tokens"][i] = {key:value for key,value in obj_dict["Tokens"][i].items() if value is not None}
        obj_dict['Language'] = self.Language
        return obj_dict
    
    
class LLCOperationGroupView(FormattingClass):
    def __init__(self, operation_group_name, operations, namespace):
        self.operation_group=operation_group_name
        self.operations=operations 
        self.Tokens =[]
        self.overview_tokens =[]
        self.namespace = namespace
    
    @classmethod
    def from_yaml(cls,yaml_data: Dict[str,Any],op_group,name): 
            operations = []
            for i in range(0,len(yaml_data["operationGroups"][op_group]["operations"])):
                operations.append(LLCOperationView.from_yaml(yaml_data,op_group,i,name))
            return cls(
                operation_group_name = yaml_data["operationGroups"][op_group]["language"]["default"]["name"],
                operations = operations,
                namespace=name,
            )

    def get_tokens(self):
            return self.Tokens

    def add_token(self, token):
        self.Tokens.append(token)

    #have a to_token to create the line for parameters
    def to_token(self):

        #Each operation will indent itself by 4
        self.add_new_line()
      
        if self.operation_group:
            self.add_whitespace(1)
            self.overview_tokens.append(Token(" "*4,TokenKind.Whitespace))
            #Operation Name token
            self.add_text(None,"OperationGroup",None)
            self.overview_tokens.append(Token("OperationGroup",TokenKind.Text))
            self.add_space()
            self.overview_tokens.append(Token(" ",TokenKind.Text))
            self.add_keyword(self.namespace+self.operation_group,self.operation_group,self.namespace+self.operation_group)
            self.overview_tokens.append(Token(self.operation_group,TokenKind.Keyword))

            self.add_new_line()
            self.overview_tokens.append(Token("",TokenKind.Newline))
    
            for operation in range(0,len(self.operations)):
                if self.operations[operation]:
                    self.operations[operation].to_token()
                    if operation==0:
                        self.add_whitespace(2)
                        self.overview_tokens.append(Token("  " * (4),TokenKind.Text))
                        self.add_punctuation("{")
                    self.add_new_line()
                    self.overview_tokens.append(Token("",TokenKind.Newline))
                    self.add_whitespace(2)
                    for i in self.operations[operation].overview_tokens:
                        self.overview_tokens.append(i)
                    for t in self.operations[operation].get_tokens():
                        self.add_token(t)
            self.add_whitespace(2)
            self.add_punctuation("}")
            self.add_new_line(1)
            self.overview_tokens.append(Token(" ",TokenKind.Whitespace))
            self.overview_tokens.append(Token("",TokenKind.Newline))

                
            
        else:
            for operation in range(0,len(self.operations)):
                if self.operations[operation]:
                    self.operations[operation].to_token()
                    for i in self.operations[operation].overview_tokens:
                        self.overview_tokens.append(i)
                    for t in self.operations[operation].get_tokens():
                        self.add_token(t)
                self.overview_tokens.append(Token("",TokenKind.Newline))
            
        
    def to_json(self):
        obj_dict={}
        self.to_token()
        for key in OP_FIELDS:
            obj_dict[key] = self.__dict__[key]
        return obj_dict


class LLCOperationView(FormattingClass):
    def __init__(self, operation_name, return_type, parameters,namespace, json_request=None,json_response=None, description ="", paging = "",lro=""):
        self.operation=operation_name
        self.return_type = return_type
        self.parameters=parameters #parameterview list
        self.Tokens =[]
        self.overview_tokens =[]
        self.namespace = namespace
        self.description = description
        self.paging = paging
        self.lro = lro
        self.json_request = json_request
        self.json_response = json_response

    @classmethod
    def from_yaml(cls,yaml_data: Dict[str,Any],op_group_num,op_num,namespace): 
        param = []
        pageable =None
        lro=None
        json_request={}
        json_response={}
        response_builder = {}
        code = CodeModel(rest_layer=True,no_models=True,no_operations=True,only_path_params_positional=True,options={})
        request_builder = RequestBuilder.from_yaml(yaml_data["operationGroups"][op_group_num]["operations"][op_num],code_model=code)
        response_builder = Operation.from_yaml(yaml_data["operationGroups"][op_group_num]["operations"][op_num])
        
        if yaml_data["operationGroups"][op_group_num]["operations"][op_num].get("extensions"):
            pageable = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["extensions"].get("x-ms-pageable")
            lro = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["extensions"].get("x-ms-long-running-operation")
        if pageable:
            paging_op = True
        else:
            paging_op = False  
        if lro:
            lro_op = True
        else:
            lro_op = False

        return_type = get_type(yaml_data["operationGroups"][op_group_num]["operations"][op_num]['responses'][0].get('schema',[]),paging_op)

        for i in range(0,len(yaml_data["operationGroups"][op_group_num]["operations"][op_num]["signatureParameters"])):
            param.append(LLCParameterView.from_yaml(yaml_data["operationGroups"][op_group_num]["operations"][op_num],i,namespace))
        for j in range(0, len(yaml_data['operationGroups'][op_group_num]['operations'][op_num]['requests'])):
            for i in range(0,len(yaml_data['operationGroups'][op_group_num]['operations'][op_num]['requests'][j].get('signatureParameters',[]))):
                param.append(LLCParameterView.from_yaml(yaml_data["operationGroups"][op_group_num]["operations"][op_num]['requests'][j],i,namespace))
                if build_schema(yaml_data = request_builder.parameters.json_body,code_model=code).serialization_type != "IO": 
                        json_request =build_schema(yaml_data = request_builder.parameters.json_body,code_model=code).get_json_template_representation()
                for i in response_builder.responses:
                    if i.schema:
                        if isinstance(i.schema,dict):
                            if build_schema(yaml_data = i.schema,code_model=code).serialization_type != "IO": 
                                json_response = build_schema(yaml_data = i.schema,code_model=code).get_json_template_representation()
                        else: json_response = i.schema.get_json_template_representation(code_model=code)
        
       
        description = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"].get("summary")
        if description is None:
            description = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"]["description"]

        
        return cls(
            operation_name = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"]["name"],
            parameters = param,
            return_type = return_type,
            namespace = namespace,
            description = description,
            paging = paging_op,
            lro = lro_op,
            json_request = json_request,
            json_response = json_response
        )

    def get_tokens(self):
        return self.Tokens

    def add_token(self, token):
        self.Tokens.append(token)
    
    def add_first_line(self):
        if self.paging and self.lro: 
            self.overview_tokens.append(Token("PagingLRO",TokenKind.Text))
            self.overview_tokens.append(Token("[",TokenKind.Text))
            self.add_text(None,"PagingLRO",None)
            self.add_text(None,"[",None)
 
        if self.paging:
            self.overview_tokens.append(Token("Paging",TokenKind.Text))
            self.overview_tokens.append(Token("[",TokenKind.Text))
            self.add_text(None,"Paging",None)
            self.add_text(None,"[",None)

        if self.lro:
            self.overview_tokens.append(Token("LRO",TokenKind.Text))
            self.overview_tokens.append(Token("[",TokenKind.Text))
            self.add_text(None,"LRO",None)
            self.add_text(None,"[",None)
    
        if self.return_type is None: 
            self.overview_tokens.append(Token("void",TokenKind.StringLiteral))
            self.add_stringliteral(None, "void", None)

        self.add_stringliteral(None,self.return_type,None)
        self.overview_tokens.append(Token(self.return_type,TokenKind.StringLiteral))
        if self.paging or self.lro: 
            self.add_text(None,"]",None)
            self.overview_tokens.append(Token("]",TokenKind.Text))
        
        self.add_space()
        self.overview_tokens.append(Token(" ",TokenKind.Text))
        token = Token(self.operation,TokenKind.Keyword)
        token.set_definition_id(self.namespace+self.operation)
        self.overview_tokens.append(token)
        self.add_keyword(self.namespace+self.operation,self.operation, self.namespace+self.operation)
        self.add_space
        
        self.add_new_line()
        self.add_description()
        self.add_whitespace(3)
        self.overview_tokens.append(Token("(",TokenKind.Text))
        self.add_punctuation("(")
    
    def add_description(self):
        self.add_token(Token(kind=TokenKind.StartDocGroup))
        self.add_whitespace(3)
        self.add_typename(None,self.description,None)
        self.add_new_line()
        self.add_token(Token(kind=TokenKind.EndDocGroup))

    def to_token(self):
        #Remove None Param
        self.parameters = [key for key in self.parameters if key.type]

        #Create Overview:

        #Each operation will indent itself by 4
        self.add_whitespace(1)
        self.overview_tokens.append(Token("  "*4,TokenKind.Whitespace))

        #Set up operation parameters
        if len(self.parameters)==0:
            self.add_first_line()
            self.add_new_line()
            self.add_whitespace(3)
            self.overview_tokens.append(Token(")",TokenKind.Text))
            self.add_punctuation(")")
            self.add_new_line(1)

        for param_num in range(0,len(self.parameters)):
            if self.parameters[param_num]:
                self.parameters[param_num].to_token()
            if param_num==0:
                self.add_first_line()
            self.add_new_line()

            #Add in parameter tokens
            if self.parameters[param_num]:
                self.add_whitespace(4)
                for t in self.parameters[param_num].get_tokens():
                    self.add_token(t)
                    self.overview_tokens.append(t)

            #Add in comma before the next parameter
            if param_num+1 in range(0,len(self.parameters)):
                self.parameters[param_num+1]
                self.add_punctuation(",")
                self.overview_tokens.append(Token(", ",TokenKind.Text))
                 
            #Create a new line for the next operation
            else: 
                self.add_new_line()
                self.add_whitespace(3)
                self.overview_tokens.append(Token(")",TokenKind.Text))
                self.add_punctuation(")")
                self.add_new_line(1)

                self.add_token(Token(kind=TokenKind.StartDocGroup))

                if self.json_request:
                    self.add_whitespace(3)
                    self.add_typename(None,"Request",None)
                    self.add_new_line(1)
                    request_builder(self,self.json_request)
                    self.add_new_line(1)

                if self.json_response:
                    self.add_whitespace(3)
                    self.add_typename(None,"Response",None)
                    self.add_new_line(1)
                    request_builder(self,self.json_response)
                    self.add_new_line(1)
                self.add_token(Token(kind=TokenKind.EndDocGroup))
    
    
    def to_json(self):
        obj_dict={}
        self.to_token()
        for key in OP_FIELDS:
            obj_dict[key] = self.__dict__[key]
        return obj_dict

def request_builder(self,json_request,indent=4):
        #Need towork on this to make it work for everything
        if json_request:
            if not isinstance(json_request,str):
                for i in json_request:
                    if isinstance(i,str):
                        self.add_whitespace(indent)
                        self.add_comment(None,i,None)
                        self.add_space()
                        if isinstance(json_request,list):
                            self.add_whitespace(5)
                            for j in range(0,len(json_request)):
                                request_builder(self,json_request[j],True)
                        elif isinstance(json_request[i],list):
                            self.add_new_line()
                            for j in range(0,len(json_request[i])):
                                request_builder(self,json_request[i][j],indent+1)
                        elif isinstance(json_request[i],str):
                            self.add_comment(None,json_request[i],None)
                            self.add_new_line()
                        elif isinstance(json_request[i],dict):
                            self.add_new_line()
                            #everytime this is called it needs to indent by one more, but bc it is recursive it doesn't
                            request_builder(self,json_request[i],indent+1)
                        
            else:
                self.add_new_line()
                self.add_whitespace(5)
                self.add_comment(None,json_request,None)
                self.add_new_line()
                    

class LLCParameterView(FormattingClass):
    def __init__(self, param_name, param_type, namespace, json_request = None, default=None, required = False):
        self.name = param_name
        self.type = param_type
        self.default = default
        self.required = required
        self.Tokens = []
        self.overview_tokens = []
        self.json_request = json_request
        self.namespace = namespace
    
    @classmethod
    def from_yaml(cls,yaml_data: Dict[str,Any],i,name):
            required=True
            default = None
            json_request ={}
            if yaml_data.get("signatureParameters"):
                default = yaml_data["signatureParameters"][i]["schema"].get('defaultValue')
                param_name = yaml_data["signatureParameters"][i]['language']['default']['name']
                if yaml_data["signatureParameters"][i]["schema"]['type'] == 'object':
                    param_type = get_type(yaml_data["signatureParameters"][i]["schema"]['properties'][0]['schema'])
                else:
                    param_type = get_type(yaml_data["signatureParameters"][i]["schema"])
                if param_name == 'body':
                    try:
                        param_name = yaml_data["signatureParameters"][i]["schema"]['properties'][0]['serializedName']   
                    except:
                        param_name =param_name
                if yaml_data["signatureParameters"][i].get("required"):
                    required=yaml_data["signatureParameters"][i]['required']
                else:
                    required = False
            else:
                param_type = None
                param_name = None

            return cls(
                param_type=param_type,
                param_name=param_name,
                required=required,
                namespace = name,
                default=default,
                json_request = json_request
            )
    
    def add_token(self, token):
        self.Tokens.append(token)
        
    def get_tokens(self):
        return self.Tokens
    
    def to_token(self):

        if self.type is not None:
            #Create parameter type token
            self.add_stringliteral(self.namespace+self.type,self.type,None)
            self.overview_tokens.append(Token(self.type,TokenKind.StringLiteral))

            #If parameter is optional, token for ? created
            if not self.required:
                self.add_stringliteral(None,"?",None)
                self.overview_tokens.append(Token("?",TokenKind.StringLiteral))
            self.add_space()
            self.overview_tokens.append(Token(" ",TokenKind.Text))
            #Create parameter name token
            self.add_text(None,self.name,None)
            self.overview_tokens.append(Token(self.name,TokenKind.Text))
    

            #Check if parameter has a default value or not
            if self.default is not None:
                self.add_space()
                self.overview_tokens.append(Token(" ",TokenKind.Text))
                self.add_text(None,"=",None)
                self.overview_tokens.append(Token("=",TokenKind.Text))
                self.add_space()
                self.overview_tokens.append(Token(" ",TokenKind.Text))
                self.add_text(None,str(self.default),None)
                self.overview_tokens.append(Token(str(self.default),TokenKind.Text))

    def to_json(self):
        obj_dict={}
        self.to_token()
        for key in PARAM_FIELDS:
            obj_dict[key] = self.__dict__[key]
        return obj_dict


class Kind:
    type_class = "class"
    type_enum = "enum"
    type_method = "method"
    type_module = "namespace"
    type_package = "assembly"

class NavigationTag:
    def __init__(self, kind):
        self.TypeKind = kind

class Navigation:
    """Navigation model to be added into tokens files. List of Navigation object represents the tree panel in tool"""

    def __init__(self, text, nav_id):
        self.Text = text
        self.NavigationId = nav_id
        self.ChildItems = []
        self.Tags = None

    def set_tag(self, tag):
        self.Tags = tag

    def add_child(self, child):
        self.ChildItems.append(child)

class SchemaRequest1():
    def __init__(self,media_types,parameters,namespace):
        self.parameters = parameters
        self.media_types = media_types
        self.namespace = namespace
        self.json_format = {}
        self.elements = []

    def to_json_formatting(self, parameters):
        elements1 = []
        for param in parameters:
            for index in param.get('schema'):
                if index=='properties':
                    for properties in param['schema']['properties']:
                        self.elements = (LLCParameterView(properties['serializedName'],get_type(properties['schema']),
                        self.namespace,required = properties.get('required')))
                        self.json_format[properties['serializedName']] = self.elements
                        if properties['schema'].get('elementType'):
                            for prop in properties['schema']['elementType'].get('properties'):
                                self.elements = LLCParameterView( prop['language']['default']['name'],get_type(prop["schema"]),
                                self.namespace,required=prop.get('required'))
                                self.json_format[prop['serializedName']] = self.elements
                                self.elements = self.to_json_formatting([prop])
                if index=='elementType':
                    for properties in param['schema']['elementType'].get('properties'):
                        self.elements = LLCParameterView( properties['language']['default']['name'],get_type(properties["schema"]),
                        self.namespace,required=properties.get('required'))
                        self.json_format[properties['serializedName']] = self.elements
                        self.elements = self.to_json_formatting([properties])
        return self.elements
       
    
    @classmethod
    def from_yaml(cls,yaml_data: Dict[str,Any],name):
        parameters = []
        parameters = yaml_data.get("signatureParameters", [])
        # json_request={SchemaRequest.from_yaml(yaml) for yaml in yaml_data["requests"]}
        return cls(
            media_types = None,
            parameters = parameters,
            namespace =name,
            # json_format = json_request
        )


def get_type(data,page=False):
    #Get type
    try:
        return_type = data['type']
        if return_type =='choice':
                return_type = data['choiceType']['type']
        if return_type == "dictionary":
            value = data['elementType']['type']
            if value =='object'or value =='array' or value =='dictionary': value = get_type(data['elementType'])
            return_type += "[string, "+ value +"]"    
        if return_type == "object":
            return_type = data['language']['default']['name']
            if page: return_type = get_type(data['properties'][0]['schema'],True)
        if return_type =='array':
            if data['elementType']['type'] != 'object' and data['elementType']['type'] != 'choice':
                return_type = data['elementType']['type']+ "[]"
            elif not page:
                return_type=  data['elementType']['language']['default']['name']+"[]"
            else:
                return_type=  data['elementType']['language']['default']['name']
        if return_type == 'number':
            if data['precision'] == 32:
                    return_type = "float32"
            if data['precision'] == 64:
                return_type = "float64"
        if return_type == 'integer':
            if data['precision'] == 32:
                return_type = "int32"
            if data['precision'] == 64:
                return_type = "int64"
        else: return_type = return_type
    except:
        return_type=None
    return return_type