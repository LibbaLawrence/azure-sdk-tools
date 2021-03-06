# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from typing import Any, Dict
from ._token import Token
from ._token_kind import TokenKind
from autorest.codegen.models import RequestBuilder, CodeModel, request_builder, build_schema, Operation

JSON_FIELDS = ["Name", "Version", "VersionString",
               "Navigation", "Tokens", "Diagnostics", "PackageName"]
PARAM_FIELDS = ["name", "type", "default", "optional", "indent"]
OP_FIELDS = ["operation", "parameters", "indent"]
R_TYPE = ['dictionary','string','bool','int32','int64','float32','float64','binary']

class FormattingClass:
    def add_whitespace(self, indent):
        if indent:
            self.add_token(Token(" " * (indent * 4)))

    def add_space(self):
        self.add_token(Token(" ", TokenKind.Whitespace))

    def add_new_line(self, additional_line_count=0):
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

    def add_comment(self, id, text, nav):
        token = Token(text, TokenKind.Comment)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)

    def add_typename(self, id, text, nav):
        token = Token(text, TokenKind.TypeName)
        token.DefinitionId = id
        token.NavigateToId = nav
        self.add_token(token)

    def add_stringliteral(self, id, text, nav):
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

    def __init__(self, operation_groups, pkg_name="", endpoint="endpoint", endpoint_type="string", credential="Credential", credential_type="AzureCredential"):
        self.Name = pkg_name
        self.Language = "Protocol"
        self.Tokens = []
        self.Operations = []
        self.Operation_Groups = operation_groups
        self.Navigation = []
        self.Diagnostics = []
        self.endpoint_type = endpoint_type
        self.endpoint = endpoint
        self.credential = credential
        self.credential_type = credential_type
        self.namespace = "Azure."+pkg_name

    @classmethod
    def from_yaml(cls, yaml_data: Dict[str, Any]):
        operation_groups = []
        # Iterate through Operations in OperationGroups
        for op_groups in range(0, len(yaml_data["operationGroups"])):
            operation_group_view = LLCOperationGroupView.from_yaml(
                yaml_data, op_groups, "Azure."+yaml_data["info"]["title"])
            operation_group = LLCOperationGroupView(
                operation_group_view.operation_group, operation_group_view.operations, "Azure."+yaml_data["info"]["title"])
            if operation_group.operation_group == "":
                operation_group.operation_group = "<default>"
                operation_groups.insert(0,operation_group)
            else: operation_groups.append(operation_group)

        return cls(
            operation_groups=operation_groups,
            pkg_name=yaml_data["info"]["title"],
            endpoint=yaml_data["globalParameters"][0]["language"]["default"]["name"],
            endpoint_type=yaml_data["globalParameters"][0]["schema"]["type"],
        )

    def add_token(self, token):
        self.Tokens.append(token)

    def add_operation_group(self, operation_group):
        self.Operation_Groups.append(operation_group)

    def to_token(self):
        # Create view
        # Namespace
        self.add_keyword(self.namespace, self.namespace, self.namespace)
        self.add_space()
        self.add_punctuation("{")
        self.add_new_line(1)

        # Name of client
        self.add_whitespace(1)
        self.add_keyword(self.namespace+self.Name,
                         self.Name, self.namespace+self.Name)
        self.add_punctuation("(")
        self.add_stringliteral(None, self.endpoint_type, None)
        self.add_space()
        self.add_text(None, self.endpoint, None)

        self.add_punctuation(",")
        self.add_space()
        self.add_stringliteral(None, self.credential_type, None)
        self.add_space()
        self.add_text(None, self.credential, None)

        self.add_punctuation(")")
        self.add_new_line(1)

        # Create Overview
        navigation = Navigation(None, None)
        navigation.set_tag(NavigationTag(Kind.type_package))
        overview = Navigation("Overview","overview")
        overview.set_tag(NavigationTag(Kind.type_package))
    
        self.add_typename("overview","Overview ######################################################################","overview")
        self.add_new_line()
        for operation_group in self.Operation_Groups:
            child_nav3 = Navigation(operation_group.operation_group,
                            self.namespace + operation_group.operation_group+"overview")
            child_nav3.set_tag(NavigationTag(Kind.type_class))
            overview.add_child(child_nav3)
            operation_group.to_token()
            operation_tokens = operation_group.overview_tokens
            for token in operation_tokens:
                if token:
                    self.add_token(token)
            for operation_view in operation_group.operations:
                child_nav2 = Navigation(
                operation_view.operation, self.namespace + operation_view.operation+"overview")
                child_nav2.set_tag(NavigationTag(Kind.type_method))
                child_nav3.add_child(child_nav2)
            self.add_new_line(1)

        self.add_typename("details","Details ######################################################################","details")
        self.add_new_line()
        details = self.to_child_tokens()
        
        self.add_new_line()

        self.add_punctuation("}")

        navigation.add_child(overview)
        navigation.add_child(details)
        self.add_navigation(navigation)

        return self.Tokens

    def to_child_tokens(self):
        # Set Navigation
        details = Navigation("Details", "details")
        details.set_tag(NavigationTag(Kind.type_package))
        self.add_new_line()
        for operation_group_view in self.Operation_Groups:
            # Add children
            child_nav1 = Navigation(operation_group_view.operation_group,
                                   self.namespace + operation_group_view.operation_group)
            child_nav1.set_tag(NavigationTag(Kind.type_class))
            details.add_child(child_nav1)
            op_group = operation_group_view.get_tokens()
            for token in op_group:
                self.add_token(token)
            # Set up operations and add to token

            for operation_view in operation_group_view.operations:
                 # Add operation comments
                child_nav = Navigation(
                    operation_view.operation, self.namespace + operation_view.operation)
                child_nav.set_tag(NavigationTag(Kind.type_method))
                child_nav1.add_child(child_nav)

        return details

    def to_json(self):
        obj_dict = {}
        self.to_token()
        for key in JSON_FIELDS:
            if key in self.__dict__:
                obj_dict[key] = self.__dict__[key]
        for i in range(0, len(obj_dict["Tokens"])):
            # Break down token objects into dictionary
            if obj_dict["Tokens"][i]:
                obj_dict["Tokens"][i] = {"Kind": obj_dict["Tokens"][i].Kind.value, "Value": obj_dict["Tokens"][i].Value,
                                         "NavigateToId": obj_dict["Tokens"][i].NavigateToId, "DefinitionId": obj_dict["Tokens"][i].DefinitionId}

            # Remove Null Values from Tokens
            obj_dict["Tokens"][i] = {
                key: value for key, value in obj_dict["Tokens"][i].items() if value is not None}
        obj_dict['Language'] = self.Language
        return obj_dict


class LLCOperationGroupView(FormattingClass):
    def __init__(self, operation_group_name, operations, namespace):
        self.operation_group = operation_group_name
        self.operations = operations
        self.Tokens = []
        self.overview_tokens = []
        self.namespace = namespace

    @classmethod
    def from_yaml(cls, yaml_data: Dict[str, Any], op_group, name):
        operations = []
        for i in range(0, len(yaml_data["operationGroups"][op_group]["operations"])):
            operations.append(LLCOperationView.from_yaml(
                yaml_data, op_group, i, name))
        return cls(
            operation_group_name=yaml_data["operationGroups"][op_group]["language"]["default"]["name"],
            operations=operations,
            namespace=name,
        )

    def get_tokens(self):
        return self.Tokens

    def add_token(self, token):
        self.Tokens.append(token)

    # have a to_token to create the line for parameters
    def to_token(self):

        # Each operation will indent itself by 4
        self.add_new_line()

        if self.operation_group:
            self.add_whitespace(1)
            self.overview_tokens.append(Token(" "*4, TokenKind.Whitespace))
            # Operation Name token
            self.add_text(None, "OperationGroup", None)
            self.overview_tokens.append(
                Token("OperationGroup", TokenKind.Text))
            self.add_space()
            self.overview_tokens.append(Token(" ", TokenKind.Text))
            self.add_keyword(self.namespace+self.operation_group,
                             self.operation_group, self.namespace+self.operation_group)
            token = Token(self.operation_group, TokenKind.Keyword)
            token.set_navigation_id(self.namespace+self.operation_group+"overview")
            token.set_definition_id(self.namespace+self.operation_group+"overview")
            self.overview_tokens.append(token)

            self.add_new_line()
            self.overview_tokens.append(Token("", TokenKind.Newline))

            for operation in range(0, len(self.operations)):
                if self.operations[operation]:
                    self.operations[operation].to_token()
                    if operation == 0:
                        self.add_whitespace(2)
                        self.overview_tokens.append(
                            Token("  " * (4), TokenKind.Text))
                        self.add_punctuation("{")
                    self.add_new_line()
                    self.overview_tokens.append(Token("", TokenKind.Newline))
                    self.add_whitespace(2)
                    for i in self.operations[operation].overview_tokens:
                        self.overview_tokens.append(i)
                    for t in self.operations[operation].get_tokens():
                        self.add_token(t)
            self.add_whitespace(2)
            self.add_punctuation("}")
            self.add_new_line(1)
            self.overview_tokens.append(Token(" ", TokenKind.Whitespace))
            self.overview_tokens.append(Token("", TokenKind.Newline))

        else:
            for operation in range(0, len(self.operations)):
                if self.operations[operation]:
                    self.operations[operation].to_token()
                    for i in self.operations[operation].overview_tokens:
                        self.overview_tokens.append(i)
                    for t in self.operations[operation].get_tokens():
                        self.add_token(t)
                self.overview_tokens.append(Token("", TokenKind.Newline))

    def to_json(self):
        obj_dict = {}
        self.to_token()
        for key in OP_FIELDS:
            obj_dict[key] = self.__dict__[key]
        return obj_dict


class LLCOperationView(FormattingClass):
    def __init__(self, operation_name, return_type, parameters, namespace, json_request=None, json_response=None, response_num=None, description="", paging="", lro="",yaml=None):
        self.operation = operation_name
        self.return_type = return_type
        self.parameters = parameters  # parameterview list
        self.Tokens = []
        self.overview_tokens = []
        self.namespace = namespace
        self.description = description
        self.paging = paging
        self.lro = lro
        self.json_request = json_request
        self.json_response = json_response
        self.response_num = response_num
        self.yaml = yaml

    @classmethod
    def from_yaml(cls, yaml_data: Dict[str, Any], op_group_num, op_num, namespace):
        param = []
        pageable = None
        lro = None
        json_request = {}
        json_response = {}
        response_builder = {}
        response_num = []
        code = CodeModel(rest_layer=True, no_models=True, no_operations=True,
                         only_path_params_positional=True, options={})
        request_builder = RequestBuilder.from_yaml(
            yaml_data["operationGroups"][op_group_num]["operations"][op_num], code_model=code)
        response_builder = Operation.from_yaml(
            yaml_data["operationGroups"][op_group_num]["operations"][op_num])
        
        for i in range(0,len(yaml_data["operationGroups"][op_group_num]["operations"][op_num].get('responses'))):
            response_num.append(yaml_data["operationGroups"][op_group_num]["operations"][op_num]['responses'][i]['protocol']['http']['statusCodes'])
        for i in range(0,len(yaml_data["operationGroups"][op_group_num]["operations"][op_num].get('exceptions',[]))):
            response_num.append(yaml_data["operationGroups"][op_group_num]["operations"][op_num]['exceptions'][i]['protocol']['http']['statusCodes'])

        if yaml_data["operationGroups"][op_group_num]["operations"][op_num].get("extensions"):
            pageable = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["extensions"].get(
                "x-ms-pageable")
            lro = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["extensions"].get(
                "x-ms-long-running-operation")
        if pageable:
            paging_op = True
        else:
            paging_op = False
        if lro:
            lro_op = True
        else:
            lro_op = False

        return_type = get_type(yaml_data["operationGroups"][op_group_num]
                               ["operations"][op_num]['responses'][0].get('schema', []), paging_op)

        for i in range(0, len(yaml_data["operationGroups"][op_group_num]["operations"][op_num]["signatureParameters"])):
            param.append(LLCParameterView.from_yaml(
                yaml_data["operationGroups"][op_group_num]["operations"][op_num], i, namespace))
        for j in range(0, len(yaml_data['operationGroups'][op_group_num]['operations'][op_num]['requests'])):
            for i in range(0, len(yaml_data['operationGroups'][op_group_num]['operations'][op_num]['requests'][j].get('signatureParameters', []))):
                param.append(LLCParameterView.from_yaml(
                    yaml_data["operationGroups"][op_group_num]["operations"][op_num]['requests'][j], i, namespace))
                if build_schema(yaml_data=request_builder.parameters.json_body, code_model=code).serialization_type != "IO":
                    json_request = build_schema(
                        yaml_data=request_builder.parameters.json_body, code_model=code).get_json_template_representation()
                for i in response_builder.responses:
                    if i.schema:
                        if isinstance(i.schema, dict):
                            if build_schema(yaml_data=i.schema, code_model=code).serialization_type != "IO":
                                json_response = build_schema(
                                    yaml_data=i.schema, code_model=code).get_json_template_representation()
                        else:
                            json_response = i.schema.get_json_template_representation(
                                code_model=code)

        description = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"].get(
            "summary")
        if description is None:
            description = yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"]["description"]

        return cls(
            operation_name=yaml_data["operationGroups"][op_group_num]["operations"][op_num]["language"]["default"]["name"],
            parameters=param,
            return_type=return_type,
            namespace=namespace,
            description=description,
            paging=paging_op,
            lro=lro_op,
            json_request=json_request,
            json_response=json_response,
            response_num = response_num,
            yaml = yaml_data["operationGroups"][op_group_num]["operations"][op_num]
        )

    def get_tokens(self):
        return self.Tokens

    def add_token(self, token):
        self.Tokens.append(token)

    def add_first_line(self):
        if self.paging and self.lro:
            self.overview_tokens.append(Token("PagingLro", TokenKind.Text))
            self.overview_tokens.append(Token("[", TokenKind.Text))
            self.add_text(None, "PagingLro", None)
            self.add_text(None, "[", None)

        if self.paging:
            self.overview_tokens.append(Token("Paging", TokenKind.Text))
            self.overview_tokens.append(Token("[", TokenKind.Text))
            self.add_text(None, "Paging", None)
            self.add_text(None, "[", None)

        if self.lro:
            self.overview_tokens.append(Token("lro", TokenKind.Text))
            self.overview_tokens.append(Token("[", TokenKind.Text))
            self.add_text(None, "lro", None)
            self.add_text(None, "[", None)

        if self.return_type is None:
            self.overview_tokens.append(Token("void", TokenKind.Text))
            self.add_text(None, "void", None)

        elif any(i in self.return_type for i in R_TYPE):
            self.add_text(None, self.return_type, None)
            self.overview_tokens.append(
                Token(self.return_type, TokenKind.Text))
        else:
            self.add_stringliteral(None, self.return_type, None)
            self.overview_tokens.append(
                Token(self.return_type, TokenKind.StringLiteral))
        if self.paging or self.lro:
            self.add_text(None, "]", None)
            self.overview_tokens.append(Token("]", TokenKind.Text))

        self.add_space()
        self.overview_tokens.append(Token(" ", TokenKind.Text))
        token = Token(self.operation, TokenKind.Keyword)
        token.set_definition_id(self.namespace+self.operation+"overview")
        token.set_navigation_id(self.namespace+self.operation+"overview")
        self.overview_tokens.append(token)
        self.add_keyword(self.namespace+self.operation,
                         self.operation, self.namespace+self.operation)
        self.add_space

        self.add_new_line()
        self.add_description()
        self.add_whitespace(3)
        self.overview_tokens.append(Token("(", TokenKind.Text))
        self.add_punctuation("(")

    def add_description(self):
        self.add_token(Token(kind=TokenKind.StartDocGroup))
        self.add_whitespace(3)
        self.add_typename(None, self.description, None)
        self.add_new_line()
        self.add_token(Token(kind=TokenKind.EndDocGroup))

    def to_token(self):
        # Remove None Param
        self.parameters = [key for key in self.parameters if key.type]

        # Create Overview:

        # Each operation will indent itself by 4
        self.add_whitespace(1)
        self.overview_tokens.append(Token("  "*4, TokenKind.Whitespace))

        # Set up operation parameters
        if len(self.parameters) == 0:
            self.add_first_line()
            self.add_new_line()
            self.add_whitespace(3)
            self.overview_tokens.append(Token(")", TokenKind.Text))
            self.add_punctuation(")")
            self.add_new_line(1)

        for param_num in range(0, len(self.parameters)):
            if self.parameters[param_num]:
                self.parameters[param_num].to_token()
            if param_num == 0:
                self.add_first_line()
            self.add_new_line()

            # Add in parameter tokens
            if self.parameters[param_num]:
                self.add_whitespace(4)
                for t in self.parameters[param_num].get_tokens():
                    self.add_token(t)
                    self.overview_tokens.append(t)

            # Add in comma before the next parameter
            if param_num+1 in range(0, len(self.parameters)):
                self.parameters[param_num+1]
                self.add_punctuation(",")
                self.overview_tokens.append(Token(", ", TokenKind.Text))

            # Create a new line for the next operation
            else:
                self.add_new_line()
                self.add_whitespace(3)
                self.overview_tokens.append(Token(")", TokenKind.Text))
                self.add_punctuation(")")
                self.add_new_line(1)

                self.add_token(Token(kind=TokenKind.StartDocGroup))
                
                if self.response_num:
                    self.add_whitespace(3)
                    self.add_typename(None, "Status Codes", None)
                    # self.add_new_line(1)
                    self.add_space()
                    for i in self.response_num:
                        if isinstance(i,list):
                            for j in i:
                                self.add_text(None,j,None)
                                self.add_text(None," ",None)
                        else:
                            self.add_text(None,i,None)
                            self.add_text(None," ",None)
                    self.add_new_line(1)

                if self.json_request:
                    self.add_whitespace(3)
                    self.add_typename(None, "Request", None)
                    self.add_new_line(1)
                    request_builder(self, self.json_request,self.yaml, notfirst=False)
                    self.add_new_line()
                    self.add_whitespace(4)
                    self.add_comment(None," }",None)
                    self.add_new_line(1)

                if self.json_response:
                    self.add_whitespace(3)
                    self.add_typename(None, "Response", None)
                    self.add_new_line(1)
                    request_builder(self, self.json_response,self.yaml, notfirst=False)
                    self.add_new_line()
                    self.add_whitespace(4)
                    self.add_comment(None," }",None)
                    self.add_new_line(1)
                self.add_token(Token(kind=TokenKind.EndDocGroup))

    def to_json(self):
        obj_dict = {}
        self.to_token()
        for key in OP_FIELDS:
            obj_dict[key] = self.__dict__[key]
        return obj_dict


def request_builder(self, json_request, yaml, notfirst, indent=4, name='',inner_model = []):
    inner_model = inner_model
    if isinstance(json_request,str):
        self.add_whitespace(indent)
        self.add_comment(None,json_request,None)
        self.add_new_line()
        
    if isinstance(json_request,list):
        for i in range(0,len(json_request)):
            if isinstance(json_request[i],str):     
                index = json_request[i].find("(optional)")
                param = json_request[i].split()
                if len(param)>=2:
                    if index!=-1:
                        json_request[i] ="? :"+ param[0]+"[] "
                    else:
                        json_request[i] =" : "+ param[0]+"[]"
                self.add_comment(None, json_request[i], None)
                self.add_new_line()
            else:
                # It is a list of whatever is in here:
                if "{" not in self.Tokens[len(self.Tokens)-1].Value:
                    self.add_comment(None,":",None)
                self.add_new_line()
                # self.add_comment(None,"{",None)
                request_builder(self,json_request[i],yaml, indent=indent+1,notfirst=True)  
                # self.add_comment(None,"}",None) 
        
    if isinstance(json_request,dict):
        for i in json_request:
            if indent==4:
                self.add_whitespace(indent)
                if(notfirst):
                    self.add_new_line()
                    self.add_whitespace(indent)
                    self.add_comment(None," }",None)
                    self.add_new_line()
                    self.add_whitespace(indent)
                self.add_comment(None,"model "+i,None)
                self.add_comment(None," {",None)
                notfirst=True
                name = i
            if indent>4 and not isinstance(json_request[i],str):
                self.add_new_line()
                if i == 'str':
                    if not isinstance(json_request[i],str):
                        self.add_whitespace(indent)
                        
                        m_type = get_map_type(yaml,name)
                        
                        self.add_comment(None,"Map<str, "+ m_type +">;",None)
                        self.add_new_line()
                        self.add_whitespace(indent)
                        inner_model.append("model "+m_type[:len(m_type)-2])
                        self.add_comment(None,"model "+m_type[:len(m_type)-2],None)
                else:
                    self.add_whitespace(indent)
                    self.add_comment(None,i,None)
                    name = i      
            if isinstance(json_request[i],str):
                self.add_new_line()
                self.add_whitespace(indent)
                index = json_request[i].find("(optional)")
                param = json_request[i].split()
                if i == 'str':
                    if index!=-1:
                            self.add_comment(None,"Map<str, "+ param[0] +">;",None)
                    else:
                        self.add_comment(None,"Map<str, "+ param[0] +">;",None)
                else:
                    if len(param)>=2:
                        if index!=-1:
                            json_request[i] =i+"? :"+ param[0]
                        else:
                            json_request[i] =i+ ": "+ param[0]
                    else:
                        self.add_comment(None,i+": ",None)        
                    self.add_comment(None, json_request[i], None)
                # self.add_new_line()
            else:
                # if "model" not in self.Tokens[len(self.Tokens)-2].Value:
                #     self.add_comment(None,":",None)
                # self.add_new_line()
                # if isinstance(json_request[i],dict):
                # self.add_comment(None,"{",None)    
                request_builder(self,json_request[i],yaml,indent=indent+1,notfirst=True,name=name) 
                # self.add_comment(None,"}",None) 

def get_map_type(yaml,name=''):
    #Find yaml type
    m_type = ''
    if yaml['requests'][0]['parameters']:
        for i in yaml['requests'][0]['parameters']:
            if i['schema'].get('properties',[]):
                for j in i['schema']['properties'][0]['schema'].get('properties',[]):
                    if j['serializedName'] == name:
                        m_type = get_type(j['schema']['elementType'])
    if yaml['responses'][0].get('schema'):
        for i in yaml['responses'][0]['schema'].get('properties',[]):
                    if i['serializedName'] == name:
                        m_type = get_type(i['schema']['elementType'])
    return m_type  
        
    
        
    
    
    # Need towork on this to make it work for everything
    # if json_request:
    #     if not isinstance(json_request, str):
    #         for i in json_request:
    #             if isinstance(i, str):
    #                 if len(i)>0:
    #                     self.add_whitespace(indent)
    #                     if indent==4:
    #                         self.add_comment(None, "model", None)
    #                         self.add_space()
    #                         self.add_comment(None, i, None)
    #                     else:
    #                         self.add_comment(None, i, None)
    #                         self.add_space()
    #                 if isinstance(json_request, list):
    #                     self.add_whitespace(5)
    #                     for j in range(0, len(json_request)):
    #                         request_builder(self, json_request[j], indent)
    #                 elif isinstance(json_request[i], list):
    #                     if len(json_request[i])>0:
    #                         self.add_new_line()
    #                         for j in range(0, len(json_request[i])):
    #                             request_builder(self, json_request[i][j], indent+1)
    #                 elif isinstance(json_request[i], str):
    #                     index = json_request[i].find("(optional)")
    #                     param = json_request[i].split()
    #                     if len(param)>=2:
    #                         if index!=-1:
    #                             json_request[i] ="? :"+ param[0]
    #                         else:
    #                             json_request[i] = ": "+ param[0]
    #                     self.add_comment(None, json_request[i], None)
    #                     self.add_new_line()
    #                 elif isinstance(json_request[i], dict):
    #                     if len(json_request[i])==1:
    #                         if not isinstance(json_request[i].get('str'),str):
    #                             self.add_new_line()
    #                             self.add_whitespace(indent+1)
    #                             self.add_comment(None,"Map<",None)
    #                             if isinstance(json_request[i]['str'],list): m_type = "list[]"
    #                             if isinstance(json_request[i]['str'],dict): m_type = "dict[]"
    #                             self.add_comment(None,"string,"+m_type+">",None)
    #                             indent+=1
    #                     self.add_new_line()
                        # if len(i)>0:
                        #     self.add_new_line()
                        #     request_builder(self, json_request[i], indent+1)
                        # else:
                        #     request_builder(self, json_request[i], indent)

        # else:
        #     self.add_whitespace(5)
        #     index = json_request.find("(optional)")
        #     param = json_request.split()
        #     if len(param)>=2:
        #         if index!=-1:
        #             json_request ="? :"+ param[0]
        #         else:
        #             json_request = ": "+ param[0]
        #     self.add_comment(None, json_request, None)
        #     self.add_new_line()


class LLCParameterView(FormattingClass):
    def __init__(self, param_name, param_type, namespace, json_request=None, default=None, required=False):
        self.name = param_name
        self.type = param_type
        self.default = default
        self.required = required
        self.Tokens = []
        self.overview_tokens = []
        self.json_request = json_request
        self.namespace = namespace

    @classmethod
    def from_yaml(cls, yaml_data: Dict[str, Any], i, name):
        required = True
        default = None
        json_request = {}
        if yaml_data.get("signatureParameters"):
            default = yaml_data["signatureParameters"][i]["schema"].get(
                'defaultValue')
            param_name = yaml_data["signatureParameters"][i]['language']['default']['name']
            if yaml_data["signatureParameters"][i]["schema"]['type'] == 'object':
                param_type = get_type(
                    yaml_data["signatureParameters"][i]["schema"]['properties'][0]['schema'])
            else:
                param_type = get_type(
                    yaml_data["signatureParameters"][i]["schema"])
            if param_name == 'body':
                try:
                    param_name = yaml_data["signatureParameters"][i]["schema"]['properties'][0]['serializedName']
                except:
                    param_name = param_name
            if yaml_data["signatureParameters"][i].get("required"):
                required = yaml_data["signatureParameters"][i]['required']
            else:
                required = False
        else:
            param_type = None
            param_name = None

        return cls(
            param_type=param_type,
            param_name=param_name,
            required=required,
            namespace=name,
            default=default,
            json_request=json_request
        )

    def add_token(self, token):
        self.Tokens.append(token)

    def get_tokens(self):
        return self.Tokens

    def to_token(self):

        if self.type is not None:
            # Create parameter type token
            self.add_stringliteral(None, self.type, None)
            self.overview_tokens.append(
                Token(self.type, TokenKind.StringLiteral))

            # If parameter is optional, token for ? created
            if not self.required:
                self.add_stringliteral(None, "?", None)
                self.overview_tokens.append(
                    Token("?", TokenKind.StringLiteral))
            self.add_space()
            self.overview_tokens.append(Token(" ", TokenKind.Text))
            # Create parameter name token
            self.add_text(self.namespace+self.type, self.name, None)
            token = Token(self.name, TokenKind.Text)
            token.set_navigation_id(self.name+"overview")
            self.overview_tokens.append(token)

            # Check if parameter has a default value or not
            if self.default is not None:
                self.add_space()
                self.overview_tokens.append(Token(" ", TokenKind.Text))
                self.add_text(None, "=", None)
                self.overview_tokens.append(Token("=", TokenKind.Text))
                self.add_space()
                self.overview_tokens.append(Token(" ", TokenKind.Text))
                if self.type == "string":
                    self.add_text(None, "'"+str(self.default)+"'", None)
                    self.overview_tokens.append(
                        Token("'"+str(self.default)+"'", TokenKind.Text))
                else:
                    self.add_text(None, str(self.default), None)
                    self.overview_tokens.append(
                        Token(str(self.default), TokenKind.Text))

    def to_json(self):
        obj_dict = {}
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


def get_type(data, page=False):
    # Get type
    try:
        return_type = data['type']
        if return_type == 'choice':
            return_type = data['choiceType']['type']
        if return_type == "dictionary":
            value = data['elementType']['type']
            if value == 'object' or value == 'array' or value == 'dictionary':
                value = get_type(data['elementType'])
            return_type += "[string, " + value + "]"
        if return_type == "object":
            return_type = data['language']['default']['name']
            if page:
                return_type = get_type(data['properties'][0]['schema'], True)
        if return_type == 'array':
            if data['elementType']['type'] != 'object' and data['elementType']['type'] != 'choice':
                return_type = data['elementType']['type'] + "[]"
            elif not page:
                return_type = data['elementType']['language']['default']['name']+"[]"
            else:
                return_type = data['elementType']['language']['default']['name']
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
        if return_type == 'boolean':
            return_type = "bool"
        else:
            return_type = return_type
    except:
        return_type = None
    return return_type
